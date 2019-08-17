import React, {Component} from 'react';
import './App.scss';

import axios, { post } from 'axios';

// react semantic ui
import { Label, Grid, Tab, Button, Card, Table, List, Menu, Input, Divider, Form, Sidebar, Segment, Header, Popup, Dropdown } from 'semantic-ui-react';

// vis tools
import { Sankey } from 'react-vis';
import ReactMapGL from 'react-map-gl';
import { StaticMap } from 'react-map-gl';
import DeckGL from '@deck.gl/react';
import { LineLayer, ColumnLayer } from '@deck.gl/layers';

import 'mapbox-gl/dist/mapbox-gl.css';

// Use default plotly-dist to create Plotly component
import Plotly from 'plotly.js-dist';
import createPlotlyComponent from 'react-plotly.js/factory';
// import Plot from 'react-plotly.js';
const Plot = createPlotlyComponent(Plotly);

class App extends Component {

  constructor(props) {
    super(props);

    this.state = {
      mapbox_access_token: 'pk.eyJ1IjoiamlzdW5nbGltIiwiYSI6ImNqdDlmM3Y0YTBpd3M0YXRoM3NoeThoZjQifQ.N6OE3k-pAOvhNsmAYx51LQ',
      initial_view_state: {
        longitude: -122.41669,
        latitude: 37.7853,
        zoom: 13,
        pitch: 0,
        bearing: 0
      },
      line_layer: {
        id: 'line-layer',
        data: [{ sourcePosition: [-122.41669, 37.7853], targetPosition: [-122.41669, 37.781] }]
      },
      column_layer: {
        id: 'column-layer',
        data: [{ value: 0.1, centroid: [-122.41669, 37.7853]}],
        diskResolution: 12,
        radius: 250,
        extruded: true,
        pickable: true,
        elevationScale: 5000,
        getPosition: d => d.centroid,
        getColor: d => [48, 128, d.value * 255, 255],
        getElevation: d => d.value,
        onHover: ({ object, x, y }) => {
          // if (!!object) {
          //   console.log(`height: ${object.value * 5000}m`);
          // }
          // const tooltip = `height: ${object.value * 5000}m`;
          /* Update tooltip
             http://deck.gl/#/documentation/developer-guide/adding-interactivity?section=example-display-a-tooltip-for-hovered-object
          */
        },
        onClick: ({ object, x, y }) => {
          if (!!object) {
            console.log(`height: ${object.value * 5000}m`);
          }
        }
      }

    };
  }


  componentDidMount() {
    console.log('component has been mounted!');

    fetch('https://raw.githubusercontent.com/uber-common/deck.gl-data/master/website/hexagons.json')
      .then(response => response.json())
      // .then(data => console.log(data));
      .then(data => {
        let column_layer = Object.assign(this.state.column_layer, {data: data});
        this.setState({ column_layer: column_layer });
        this.forceUpdate();
      });
  }

  handleViewportChange = (viewport) => {
    console.log('viewport has been changed!');
    this.setState({ viewport });
  }

  render() {
    // const { viewport } = this.state;
    const layers = [
      new LineLayer(this.state.line_layer),
      new ColumnLayer(this.state.column_layer)
    ];

    return (
      <div className='view-panel'>
        <div className='view-panel__map'>
          <DeckGL
            className='dashboard'
            initialViewState={this.state.initial_view_state}
            controller={true}
            layers={layers}
          >
            <StaticMap
              className='dashboard__map-layer'
              mapboxApiAccessToken={this.state.mapbox_access_token}
              onViewportChange={this.handViewportChange} />
          </DeckGL>
        </div>
        <div className='view-panel__chart'>
        
        </div>
        

        {/* <div className='dashboard'>
          <ReactMapGL
            className='dashboard__map'
            {...this.state.viewport}
            mapboxApiAccessToken='pk.eyJ1IjoiamlzdW5nbGltIiwiYSI6ImNqdDlmM3Y0YTBpd3M0YXRoM3NoeThoZjQifQ.N6OE3k-pAOvhNsmAYx51LQ'
            onViewportChange={this.handViewportChange} />
        </div> */}
      </div>
    );
  }
}

export default App;
