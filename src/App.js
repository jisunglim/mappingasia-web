import React, {Component} from 'react';
import './App.scss';

import axios, { post } from 'axios';

// react semantic ui
import { 
  Divider, Image, Dropdown, Item, Header,
  Label, Grid, Tab, Button, Card, Table, List, Menu, Input, Form, Sidebar, Segment, Popup 
} from 'semantic-ui-react';

// vis tools
import { Sankey } from 'react-vis';
import ReactMapGL from 'react-map-gl';
import { StaticMap } from 'react-map-gl';
import DeckGL from '@deck.gl/react';
import { LineLayer, ColumnLayer, GeoJsonLayer } from '@deck.gl/layers';

import 'mapbox-gl/dist/mapbox-gl.css';

// Use default plotly-dist to create Plotly component
import Plotly from 'plotly.js-dist';
import createPlotlyComponent from 'react-plotly.js/factory';
import { thisTypeAnnotation } from '@babel/types';

// import Plot from 'react-plotly.js';
const Plot = createPlotlyComponent(Plotly);

class App extends Component {
  constructor(props) {
    super(props);

    // default handlers
    this.componentDidMount = this.componentDidMount.bind(this);
    this.componentWillUnmount = this.componentWillUnmount.bind(this);

    this.state = {
      mapbox_access_token:
        "pk.eyJ1IjoiamlzdW5nbGltIiwiYSI6ImNqdDlmM3Y0YTBpd3M0YXRoM3NoeThoZjQifQ.N6OE3k-pAOvhNsmAYx51LQ",
      initial_view_state: {
        longitude: 104.0668,
        latitude: 30.5728,
        zoom: 3,
        pitch: 0,
        bearing: 0
      },

      /* Layers */
      geojson_layer: {
        id: "country-layer",
        data: null, // To be filled async
        pickable: true,
        stroked: true,
        filled: true,
        extruded: true,
        lineWidthScale: 20,
        lineWidthMinPixels: 2,
        getFillColor: d => {
          return [160, 160, 180, 200];
        },
        getLineColor: d => {
          return [0, 0, 0, 255];
        },
        getRadius: 100,
        getLineWidth: 2,
        getElevation: 30,
        autoHighlight: true,
        highlightColor: [74, 216, 255, 255],  // Hover color
        onClick: this.handleClickCountry
      },
      /* SDG metadata */
      sdg_goals: [],
      sdg_targets: [],
      sdg_indicators: [],
      sdg_serieses: [],

      /* selected */
      selected_country: null,
      selected_goal: null,
      selected_target: null,
      selected_indicator: null,
      selected_series: null,

      /* UI / UX */
      selected_layer: {
        id: "country-layer--selected",
        data: null, // To be filled async
        pickable: true,
        stroked: true,
        filled: true,
        extruded: true,
        lineWidthScale: 20,
        lineWidthMinPixels: 2,
        getFillColor: d => [67, 113, 232, 255],
        getLineColor: d => {
          return [0, 0, 0, 255];
        },
        getRadius: 100,
        getLineWidth: 2,
        getElevation: 30,
        autoHighlight: true,
        highlightColor: [74, 216, 255, 255],  // Hover color
      },
    };
  }

  /***********************************************************
   ************ Default handler and layout handler ***********
   ***********************************************************/
  componentDidMount() {
    console.log("component has been mounted!");

    fetch("rsc/countries_10m.geo.json")
      .then(fp => fp.json())
      .then(data => {
        let old = this.state.geojson_layer;
        old.data = data;
        this.setState({ geojson_layer: old });
      });

    fetch("http://localhost:5000/sdg_goals")
      .then(response => response.json())
      .then(goals =>
        goals.map(goal => {
          return {
            key: goal.id,
            text: `SDG ${goal.id_str}`,
            value: goal.id,
            image: { src: `img/E_SDG_Icons-${goal.id_str}.png` }
          };
        })
      )
      .then(goals => this.setState({ sdg_goals: goals }));

    this._setCountry('KOR');  // FIXME: ad-hoc
  }

  componentWillUnmount() {
    console.log("component will be unmounted!");
  }

  handleViewportChange = viewport => {
    console.log("viewport has been changed!");
    this.setState({ viewport });
  };

  
  handleClickCountry = ({ color, layer, object, picked, x, y }) => {
    if (!!object) {
      let old = this.state.selected_layer;
      old.data = object;
      this.setState({ selected_layer: old });

      console.log(object);
      let iso_a3 = object.properties.iso_a3;
      this._setCountry(iso_a3);
    }
  };

  _setCountry = (iso_a3) => {
    fetch(`http://localhost:5000/country_by_iso_a3/${iso_a3}`)
      .then(response => response.json())
      .then(country => {
        country.flag_url = `https://www.countryflags.io/${country.iso_a2.toLowerCase()}/flat/64.png`
        console.log(country);
        return country;
      })
      .then(country => this.setState({ selected_country: country }));
  }

  handleGoalChange = (e, { value }) => {
    const selected_goal = value;
    this.setState({ selected_goal });
    fetch(`http://localhost:5000/sdg_targets_by_goal_id/${selected_goal}`)
      .then(response => response.json())
      .then(targets =>
        targets.map(target => {
          return {
            key: target.id,
            text: `Target ${target.id}`,
            value: target.id
          };
        })
      )
      .then(targets => this.setState({ sdg_targets: targets }));

    fetch(`http://localhost:5000/sdg_indicators_by_goal_id/${selected_goal}`)
      .then(response => response.json())
      .then(indicators =>
        indicators.map(indicator => {
          return {
            key: indicator.id,
            text: `Indicator ${indicator.id}`,
            value: indicator.id
          };
        })
      )
      .then(indicators => this.setState({ sdg_indicators: indicators }));
  };

  handleTargetChange = (e, { value }) => {
    const selected_target = value;
    this.setState({ selected_target });
    fetch(
      `http://localhost:5000/sdg_indicators_by_target_id/${selected_target}`
    )
      .then(response => response.json())
      .then(indicators =>
        indicators.map(indicator => {
          return {
            key: indicator.id,
            text: `Indicator ${indicator.id}`,
            value: indicator.id
          };
        })
      )
      .then(indicators => this.setState({ sdg_indicators: indicators }));
  };

  handleIndicatorChange = (e, { value }) => {
    const selected_indicator = value;
    this.setState({ selected_indicator });
  };

  render() {
    // const { viewport } = this.state;

    return (
      <div className="view-panel">
        <div className="view-panel__map">
          <DeckGL
            className="dashboard"
            initialViewState={this.state.initial_view_state}
            controller={true}
            layers={this.state.layers}
          >
            <StaticMap
              className="dashboard__map-layer"
              mapboxApiAccessToken={this.state.mapbox_access_token}
              onViewportChange={this.handViewportChange}
            />
            <GeoJsonLayer
              className="dashboard__country-layer"
              {...this.state.geojson_layer}
            />
            <GeoJsonLayer
              className="dashboard__country-layer--selected"
              {...this.state.selected_layer}
            />
          </DeckGL>
        </div>
        <div className="view-panel__chart">
          <div>
            <div>
              {this.state.selected_country == null ? (
                <div />
              ) : (
                <React.Fragment>
                  <Item.Group>
                    <Item>
                      <Item.Image
                        size="tiny" bordered
                        src={this.state.selected_country.flag_url}
                      />
                      <Item.Content>
                        <Item.Header as="a">
                          {this.state.selected_country.name}
                        </Item.Header>
                        <Item.Extra>
                          <Label color="blue">
                            ISO-3166-1-alpha-3
                            <Label.Detail>{this.state.selected_country.iso_a3}</Label.Detail>
                          </Label>
                          <Label color="yellow">
                            language
                            <Label.Detail>{this.state.selected_country.lang.split(',')[0]}</Label.Detail>
                          </Label>
                          <Label>{this.state.selected_country.region_name}</Label>
                          <Label>{this.state.selected_country.subregion_name}</Label>
                          <Label>{this.state.selected_country.developed_developing}</Label>
                        </Item.Extra>
                      </Item.Content>
                    </Item>
                  </Item.Group>
                </React.Fragment>
              )}
            </div>
          </div>
        </div>
        <div className='view-panel__float'>
          <React.Fragment>
            <Dropdown
              placeholder="Select Your Goal"
              closeOnEscape
              selection
              header="SDG: GOALS"
              options={this.state.sdg_goals}
              onChange={this.handleGoalChange}
              value={this.state.selected_goal}
            />{" "}
            <Dropdown
              placeholder="Select Target"
              closeOnEscape
              selection
              header="SDG: TARGETS"
              options={this.state.sdg_targets}
              onChange={this.handleTargetChange}
              value={this.state.selected_target}
            />{" "}
            <Dropdown
              placeholder="Select Indicator"
              closeOnEscape
              selection
              header="SDG: INDICATORS"
              options={this.state.sdg_indicators}
              onChange={this.handleIndicatorChange}
              value={this.state.selected_indicator}
            />
          </React.Fragment>
        </div>
      </div>
    );
  }
}

export default App;
