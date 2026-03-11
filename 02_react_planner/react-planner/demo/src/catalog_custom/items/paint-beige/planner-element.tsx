import React from 'react';
import { BoxGeometry, MeshBasicMaterial, Mesh, BoxHelper } from 'three';

export default {
  name: 'paint-beige',
  prototype: 'items',

  info: {
    title: 'Beige Paint',
    tag: ['painting'],
    description: 'Internal beige paint',
    image: ''
  },

  properties: {
    color: {
      label: 'Color',
      type: 'color',
      defaultValue: '#e6d3b3'
    }
  },

  render2D: (element: any) => {
    const style = {
      stroke: '#000',
      strokeWidth: element.selected ? '2px' : '0px',
      fill: element.properties.get('color')
    };

    return (
      <g transform="translate(-50, -50)">
        <rect x="0" y="0" width="100" height="100" style={style} />
      </g>
    );
  },

  render3D: (element: any) => {
    const geometry = new BoxGeometry(100, 100, 100);
    const material = new MeshBasicMaterial({
      color: element.properties.get('color')
    });

    const mesh = new Mesh(geometry, material);

    if (element.selected) {
      const box = new BoxHelper(mesh, '#000');
      box.material.linewidth = 1;
      box.material.depthTest = false;
      box.renderOrder = 1000;
      mesh.add(box);
    }

    mesh.position.y = 50;

    return Promise.resolve(mesh);
  }
};