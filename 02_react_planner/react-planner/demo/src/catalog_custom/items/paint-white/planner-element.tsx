import React from 'react';

import { defineCatalogElement } from '@archef2000/react-planner';
import { BoxGeometry, BoxHelper, Mesh, MeshBasicMaterial } from 'three';

export default defineCatalogElement({
  name: 'paint-white',
  prototype: 'items',

  info: {
    title: 'White Paint',
    tag: ['painting'],
    description: 'Internal white paint',
    image: '',
    mainService: 'painting',
    subService: 'Internal paint'
  } as any,

  properties: {
    color: {
      label: 'Color',
      type: 'color',
      defaultValue: '#ffffff'
    }
  },

  render2D: (element) => {
    const style = {
      stroke: '#000',
      strokeWidth: 2,
      fill: element.properties.color
    } as const;

    return (
      <g transform="translate(-50, -50)">
        <rect x="0" y="0" width="100" height="100" style={style} />
      </g>
    );
  },

  async render3D(element) {
    const geometry = new BoxGeometry(100, 100, 100);
    const material = new MeshBasicMaterial({
      color: element.properties.color
    });

    const mesh = new Mesh(geometry, material);

    const box = new BoxHelper(mesh, '#000');
    box.material.linewidth = 1;
    box.material.depthTest = false;
    box.renderOrder = 1000;
    mesh.add(box);

    mesh.position.y = 50;

    return mesh;
  }
});