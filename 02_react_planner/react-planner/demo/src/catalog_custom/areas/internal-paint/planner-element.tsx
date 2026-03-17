import {
  CatalogElementInfo,
  CatalogElementTextures,
  ElementsFactories
} from '@archef2000/react-planner';

const info: CatalogElementInfo = {
  title: 'internal paint',
  tag: ['painting'],
  description: 'Internal wall paint',
  image: ''
};

const textures: CatalogElementTextures = {
  white_paint: {
    name: 'White Paint',
    uri: require('../area/textures/grass.jpg'),
    lengthRepeatScale: 0.002,
    heightRepeatScale: 0.002
  },
  light_grey_paint: {
    name: 'Light Grey Paint',
    uri: require('../area/textures/tile1.jpg'),
    lengthRepeatScale: 0.002,
    heightRepeatScale: 0.002
  },
  beige_paint: {
    name: 'Beige Paint',
    uri: require('../area/textures/parquet.jpg'),
    lengthRepeatScale: 0.002,
    heightRepeatScale: 0.002
  }
};

export default ElementsFactories.AreaFactory('internal-paint', info, textures);