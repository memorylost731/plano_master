import React, { Component } from 'react';

import convert from 'convert-units';
import { produce } from 'immer';
import { MdContentCopy, MdContentPaste } from 'react-icons/md';

import { CatalogFn } from '../../../catalog/catalog';
import { Area, Item, Layer, StateProps } from '../../../models';
import ReactPlannerContext, {
  ReactPlannerContextProps
} from '../../../react-planner-context';
import * as SharedStyle from '../../../shared-style';
import {
  CatalogElementProperty,
  ElementType,
  HoleAttributes,
  LineAttributes
} from '../../../types';
import { GeometryUtils, MathUtils } from '../../../utils/export';

import AttributesEditor from './attributes-editor/attributes-editor';

const PRECISION = 2;

const attrPorpSeparatorStyle = {
  margin: '0.5em 0.25em 0.5em 0',
  border: '2px solid ' + SharedStyle.SECONDARY_COLOR.alt,
  position: 'relative',
  height: '2.5em',
  borderRadius: '2px'
} as const;

const headActionStyle = {
  position: 'absolute',
  right: '0.5em',
  top: '0.5em'
} as const;

const iconHeadStyle = {
  float: 'right',
  margin: '-3px 4px 0px 0px',
  padding: 0,
  cursor: 'pointer',
  fontSize: '1.4em'
} as const;

const infoRowStyle = {
  margin: '0.4em 0.25em 0.6em 0.25em',
  padding: '0.5em 0.6em',
  borderRadius: '6px',
  background: 'rgba(255,255,255,0.06)',
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center'
} as const;

const infoLabelStyle = { opacity: 0.85 } as const;
const infoValueStyle = { fontWeight: 700 } as const;

const estimatorBoxStyle = {
  margin: '0.4em 0.25em 0.6em 0.25em',
  padding: '0.6em 0.6em',
  borderRadius: '6px',
  background: 'rgba(255,255,255,0.06)'
} as const;

const estimatorHeaderStyle = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  marginBottom: '0.4em'
} as const;

const estimatorTitleStyle = {
  fontWeight: 700,
  opacity: 0.9
} as const;

const estimatorActionsStyle = {
  display: 'flex',
  gap: '0.4em'
} as const;

const miniBtnStyle = {
  border: '1px solid ' + SharedStyle.SECONDARY_COLOR.alt,
  background: 'transparent',
  color: 'inherit',
  borderRadius: '6px',
  padding: '0.25em 0.5em',
  cursor: 'pointer',
  fontWeight: 700,
  opacity: 0.9
} as const;

const miniBtnDisabledStyle = {
  ...miniBtnStyle,
  opacity: 0.35,
  cursor: 'not-allowed'
} as const;

const estimatorRowStyle = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  padding: '0.25em 0'
} as const;

const estimatorItemStyle = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  gap: '0.6em',
  padding: '0.25em 0',
  borderTop: '1px solid rgba(255,255,255,0.08)'
} as const;

const removeBtnStyle = {
  ...miniBtnStyle,
  padding: '0.15em 0.45em'
} as const;

interface ElementEditorProps {
  state: StateProps;
  element: ElementType;
  layer: Layer;
}

type PropertyForm = {
  currentValue: Record<string, any>;
  configs: Record<string, any>;
};

export type AttributesFormData = Item | LineAttributes | HoleAttributes | Area;

type ElementEditorState = {
  attributesFormData: AttributesFormData;
  propertiesFormData: Record<string, PropertyForm>;
};

type SurfaceBasketItem = {
  id: string;
  label: string;
  m2: number;
  ts: number;
};

export default class ElementEditor extends Component<
  ElementEditorProps,
  ElementEditorState
> {
  static contextType = ReactPlannerContext;
  context!: React.ContextType<typeof ReactPlannerContext>;

  constructor(props: ElementEditorProps, context: ReactPlannerContextProps) {
    super(props, context);

    this.state = {
      attributesFormData: this.initAttrData(
        this.props.element,
        this.props.layer,
        context
      ),
      propertiesFormData: this.initPropData(this.props.element, context)
    };

    this.updateAttribute = this.updateAttribute.bind(this);
    this.addCurrentSurfaceToBasket = this.addCurrentSurfaceToBasket.bind(this);
    this.clearSurfaceBasket = this.clearSurfaceBasket.bind(this);
  }

  shouldComponentUpdate(
    nextProps: ElementEditorProps,
    nextState: ElementEditorState
  ) {
    if (
      this.state.attributesFormData !== nextState.attributesFormData ||
      this.state.propertiesFormData !== nextState.propertiesFormData ||
      this.props.state.clipboardProperties !==
        nextProps.state.clipboardProperties
    )
      return true;

    return false;
  }

  componentDidUpdate(prevProps: ElementEditorProps) {
    const { element, layer } = this.props;

    if (prevProps.layer.id !== layer.id) {
      this.setState({
        attributesFormData: this.initAttrData(element, layer, this.context),
        propertiesFormData: this.initPropData(element, this.context)
      });
    }
  }

  initAttrData(
    element: ElementType,
    layer: Layer,
    context: ReactPlannerContextProps
  ) {
    switch (element.prototype) {
      case 'items': {
        return element;
      }
      case 'lines': {
        const v_a = layer.vertices[element.vertices[0]];
        const v_b = layer.vertices[element.vertices[1]];

        const distance = GeometryUtils.pointsDistance(
          v_a.x,
          v_a.y,
          v_b.x,
          v_b.y
        );
        const _unit = (element as any).misc?._unitLength || context.catalog.unit;
        const _length = convert(distance).from(context.catalog.unit).to(_unit);

        return {
          vertexOne: v_a,
          vertexTwo: v_b,
          lineLength: { length: distance, _length, _unit }
        } as LineAttributes;
      }
      case 'holes': {
        const line = layer.lines[(element as any).line];
        const { x: x0, y: y0 } = layer.vertices[line.vertices[0]];
        const { x: x1, y: y1 } = layer.vertices[line.vertices[1]];
        const lineLength = GeometryUtils.pointsDistance(x0, y0, x1, y1);
        const startAt =
          lineLength * (element as any).offset -
          (element as any).properties.width.length / 2;

        const _unitA = (element as any).misc?._unitA || context.catalog.unit;
        const _lengthA = convert(startAt).from(context.catalog.unit).to(_unitA);

        const endAt =
          lineLength -
          lineLength * (element as any).offset -
          (element as any).properties.width.length / 2;
        const _unitB = (element as any).misc?._unitB || context.catalog.unit;
        const _lengthB = convert(endAt).from(context.catalog.unit).to(_unitB);

        return {
          offset: (element as any).offset,
          offsetA: {
            length: MathUtils.toFixedFloat(startAt, PRECISION),
            _length: MathUtils.toFixedFloat(_lengthA, PRECISION),
            _unit: _unitA
          },
          offsetB: {
            length: MathUtils.toFixedFloat(endAt, PRECISION),
            _length: MathUtils.toFixedFloat(_lengthB, PRECISION),
            _unit: _unitB
          }
        } as HoleAttributes;
      }
      case 'areas': {
        return element;
      }
    }
  }

  initPropData(element: ElementType, context: ReactPlannerContextProps) {
    const { catalog } = context;
    const catalogElement = CatalogFn.getElement(catalog, (element as any).type);

    type Result = Record<
      string,
      { currentValue: any; configs: CatalogElementProperty }
    >;
    const mapped: Result = {};

    for (const name in catalogElement.properties) {
      const propDef = catalogElement.properties[name];
      const defVal =
        propDef && typeof propDef === 'object' && 'defaultValue' in propDef
          ? (propDef as { defaultValue: any }).defaultValue
          : undefined;
      mapped[name] = {
        currentValue: (element as any).properties?.[name] ?? defVal,
        configs: propDef
      };
    }
    return mapped;
  }

  updateAttribute(attributeName: string, value: any) {
    const { attributesFormData: oldAttributesFormData } = this.state;
    let newAttributesFormData: ElementEditorState['attributesFormData'];

    switch ((this.props.element as any).prototype) {
      case 'items': {
        newAttributesFormData = {
          ...oldAttributesFormData,
          [attributeName]: value
        };
        break;
      }
      case 'lines': {
        let attributesFormData = oldAttributesFormData as LineAttributes;
        switch (attributeName) {
          case 'lineLength': {
            const v_0 = (attributesFormData as any).vertexOne;
            const v_1 = (attributesFormData as any).vertexTwo;

            const [v_a, v_b] = GeometryUtils.orderVertices([v_0, v_1]);

            const v_b_new = GeometryUtils.extendLine(
              v_a.x,
              v_a.y,
              v_b.x,
              v_b.y,
              value.length,
              PRECISION
            );

            attributesFormData = produce(attributesFormData, (attr: any) => {
              if (v_0 === v_a) {
                attr.vertexTwo = { ...v_b, ...v_b_new };
              } else {
                attr.vertexOne = { ...v_b, ...v_b_new };
              }
              attr.lineLength = value;
            });
            break;
          }
          case 'vertexOne':
          case 'vertexTwo': {
            attributesFormData = produce(attributesFormData, (attr: any) => {
              attr[attributeName] = {
                ...attr[attributeName],
                ...value
              };

              const newDistance = GeometryUtils.verticesDistance(
                attr.vertexOne,
                attr.vertexTwo
              );
              attr.lineLength = {
                ...attr.lineLength,
                length: newDistance,
                _length: convert(newDistance)
                  .from(this.context.catalog.unit)
                  .to(attr.lineLength._unit)
              };
            });
            break;
          }
          default: {
            attributesFormData = {
              ...attributesFormData,
              [attributeName]: value
            };
            break;
          }
        }
        newAttributesFormData = attributesFormData;
        break;
      }
      case 'holes': {
        let attributesFormData = oldAttributesFormData as HoleAttributes;
        switch (attributeName) {
          case 'offsetA': {
            const line = this.props.layer.lines[(this.props.element as any).line];

            const orderedVertices = GeometryUtils.orderVertices([
              this.props.layer.vertices[line.vertices[0]],
              this.props.layer.vertices[line.vertices[1]]
            ]);

            const [{ x: x0, y: y0 }, { x: x1, y: y1 }] = orderedVertices;

            const alpha = GeometryUtils.angleBetweenTwoPoints(x0, y0, x1, y1);
            const lineLength = GeometryUtils.pointsDistance(x0, y0, x1, y1);
            const widthLength = (this.props.element as any).properties.width.length;
            const halfWidthLength = widthLength / 2;

            let lengthValue = value.length;
            lengthValue = Math.max(lengthValue, 0);
            lengthValue = Math.min(lengthValue, lineLength - widthLength);

            const xp = (lengthValue + halfWidthLength) * Math.cos(alpha) + x0;
            const yp = (lengthValue + halfWidthLength) * Math.sin(alpha) + y0;

            const offset = GeometryUtils.pointPositionOnLineSegment(
              x0, y0, x1, y1, xp, yp
            );

            const endAt = MathUtils.toFixedFloat(
              lineLength - lineLength * offset - halfWidthLength,
              PRECISION
            );
            const offsetUnit = (attributesFormData as any).offsetB._unit;

            const offsetB = {
              length: endAt,
              _length: convert(endAt)
                .from(this.context.catalog.unit)
                .to(offsetUnit),
              _unit: offsetUnit
            };

            const offsetA = {
              length: MathUtils.toFixedFloat(lengthValue, PRECISION),
              _unit: value._unit,
              _length: MathUtils.toFixedFloat(
                convert(lengthValue)
                  .from(this.context.catalog.unit)
                  .to(value._unit),
                PRECISION
              )
            };

            attributesFormData = {
              ...(attributesFormData as any),
              offsetB,
              offset,
              offsetA
            } as any;
            break;
          }
          case 'offsetB': {
            const line = this.props.layer.lines[(this.props.element as any).line];

            const orderedVertices = GeometryUtils.orderVertices([
              this.props.layer.vertices[line.vertices[0]],
              this.props.layer.vertices[line.vertices[1]]
            ]);

            const [{ x: x0, y: y0 }, { x: x1, y: y1 }] = orderedVertices;

            const alpha = GeometryUtils.angleBetweenTwoPoints(x0, y0, x1, y1);
            const lineLength = GeometryUtils.pointsDistance(x0, y0, x1, y1);
            const widthLength = (this.props.element as any).properties.width.length;
            const halfWidthLength = widthLength / 2;

            let lengthValue = value.length;
            lengthValue = Math.max(lengthValue, 0);
            lengthValue = Math.min(lengthValue, lineLength - widthLength);

            const xp = x1 - (lengthValue + halfWidthLength) * Math.cos(alpha);
            const yp = y1 - (lengthValue + halfWidthLength) * Math.sin(alpha);

            const offset = GeometryUtils.pointPositionOnLineSegment(
              x0, y0, x1, y1, xp, yp
            );

            const startAt = MathUtils.toFixedFloat(
              lineLength * offset - halfWidthLength,
              PRECISION
            );
            const offsetUnit = (attributesFormData as any).offsetA._unit;

            const offsetA = {
              length: startAt,
              _length: convert(startAt)
                .from(this.context.catalog.unit)
                .to(offsetUnit),
              _unit: offsetUnit
            };

            const offsetB = {
              length: MathUtils.toFixedFloat(lengthValue, PRECISION),
              _unit: value._unit,
              _length: MathUtils.toFixedFloat(
                convert(lengthValue)
                  .from(this.context.catalog.unit)
                  .to(value._unit),
                PRECISION
              )
            };

            attributesFormData = {
              ...(attributesFormData as any),
              offsetA,
              offset,
              offsetB
            } as any;

            break;
          }
          default: {
            attributesFormData = {
              ...(attributesFormData as any),
              [attributeName]: value
            } as any;
            break;
          }
        }
        newAttributesFormData = attributesFormData;
        break;
      }
      case 'areas': {
        newAttributesFormData = {
          ...oldAttributesFormData,
          [attributeName]: value
        };
        break;
      }
      default:
        newAttributesFormData = oldAttributesFormData;
        break;
    }

    this.setState({ attributesFormData: newAttributesFormData });
    this.save({ attributesFormData: newAttributesFormData });
  }

  updateProperty(propertyName: string, value: any) {
    let {
      state: { propertiesFormData }
    } = this;
    propertiesFormData = produce(propertiesFormData, (draft: any) => {
      draft[propertyName].currentValue = value;
    });
    this.setState({ propertiesFormData });
    this.save({ propertiesFormData });
  }

  reset() {
    this.setState({
      propertiesFormData: this.initPropData(this.props.element, this.context)
    });
  }

  save({ propertiesFormData, attributesFormData }: Partial<ElementEditorState>) {
    if (propertiesFormData) {
      const properties = Object.keys(propertiesFormData).reduce((acc, key) => {
        const data = (propertiesFormData as any)[key];
        acc[key] =
          data && data.currentValue !== undefined ? data.currentValue : undefined;
        return acc;
      }, {} as Record<string, any>);

      this.context.projectActions.setProperties(properties);
    }

    if (attributesFormData) {
      switch ((this.props.element as any).prototype) {
        case 'items': {
          this.context.projectActions.setItemsAttributes(attributesFormData as Item);
          break;
        }
        case 'lines': {
          this.context.projectActions.setLinesAttributes(attributesFormData as LineAttributes);
          break;
        }
        case 'holes': {
          this.context.projectActions.setHolesAttributes(attributesFormData as HoleAttributes);
          break;
        }
        case 'areas': {
          this.context.projectActions.setAreasAttributes(attributesFormData as Area);
          break;
        }
      }
    }
  }

  copyProperties(properties: Record<string, any>) {
    this.context.projectActions.copyProperties(properties);
  }

  pasteProperties() {
    this.context.projectActions.pasteProperties();
  }

  private computeSelectedAreaM2(): number | null {
    const { element, layer } = this.props;

    if ((element as any).prototype !== 'areas') return null;

    const vertices = (element as any).vertices;
    if (!Array.isArray(vertices) || vertices.length < 3) return null;

    const pts = vertices
      .map((vid: string) => (layer as any).vertices[vid])
      .filter(Boolean)
      .map((v: any) => ({ x: v.x, y: v.y }));

    if (pts.length < 3) return null;

    // Shoelace area in "catalog.unit^2"
    let sum = 0;
    for (let i = 0; i < pts.length; i++) {
      const j = (i + 1) % pts.length;
      sum += pts[i].x * pts[j].y - pts[j].x * pts[i].y;
    }
    const areaUnit2 = Math.abs(sum) / 2;

    // Convert to m² based on catalog unit (cm -> m)
    const unit = this.context.catalog.unit; // usually "cm"
    const metersPerUnit = convert(1).from(unit).to('m');
    const areaM2 = areaUnit2 * metersPerUnit * metersPerUnit;

    return MathUtils.toFixedFloat(areaM2, 2);
  }

  private computeSelectedWallSurfaceM2(): number | null {
    const { element, layer } = this.props;

    if ((element as any).prototype !== 'lines') return null;

    const v0 = (layer as any).vertices[(element as any).vertices?.[0]];
    const v1 = (layer as any).vertices[(element as any).vertices?.[1]];
    if (!v0 || !v1) return null;

    const lengthUnit = GeometryUtils.pointsDistance(v0.x, v0.y, v1.x, v1.y);

    // Typical wall has properties.height.length
    const heightUnit = (element as any).properties?.height?.length;
    if (typeof heightUnit !== 'number' || !isFinite(heightUnit) || heightUnit <= 0) {
      return null;
    }

    const surfaceUnit2 = lengthUnit * heightUnit;

    const unit = this.context.catalog.unit; // usually "cm"
    const metersPerUnit = convert(1).from(unit).to('m');
    const surfaceM2 = surfaceUnit2 * metersPerUnit * metersPerUnit;

    return MathUtils.toFixedFloat(surfaceM2, 2);
  }

  private getSurfaceBasket(): SurfaceBasketItem[] {
    const sceneProps = ((this.props.state as any)?.scene?.properties ?? {}) as any;
    const raw = sceneProps.surfaceBasket;
    if (!Array.isArray(raw)) return [];
    return raw
      .filter((x) => x && typeof x.m2 === 'number' && isFinite(x.m2))
      .slice(0, 200); // safety cap
  }

  private setSurfaceBasket(next: SurfaceBasketItem[]) {
    const scene = (this.props.state as any)?.scene;
    const sceneProps = (scene?.properties ?? {}) as any;

    this.context.projectActions.setProjectProperties({
      properties: {
        ...sceneProps,
        surfaceBasket: next
      }
    } as any);
  }

  private getCurrentSurface(): { label: string; m2: number } | null {
    const wallM2 = this.computeSelectedWallSurfaceM2();
    if (wallM2 !== null) return { label: 'Wall surface', m2: wallM2 };

    const areaM2 = this.computeSelectedAreaM2();
    if (areaM2 !== null) return { label: 'Area', m2: areaM2 };

    return null;
  }

  private addCurrentSurfaceToBasket() {
    const cur = this.getCurrentSurface();
    if (!cur) return;

    const basket = this.getSurfaceBasket();
    const idBase = (this.props.element as any)?.id || 'elem';
    const item: SurfaceBasketItem = {
      id: `${idBase}_${Date.now()}`,
      label: cur.label,
      m2: MathUtils.toFixedFloat(cur.m2, 2),
      ts: Date.now()
    };

    this.setSurfaceBasket([item, ...basket]);
  }

  private removeBasketItem(id: string) {
    const basket = this.getSurfaceBasket();
    const next = basket.filter((x) => x.id !== id);
    this.setSurfaceBasket(next);
  }

  private clearSurfaceBasket() {
    this.setSurfaceBasket([]);
  }

  render() {
    const {
      state: { propertiesFormData, attributesFormData },
      context: { catalog, translator },
      props: { state: appState, element }
    } = this;

    const selectedAreaM2 = this.computeSelectedAreaM2();
    const selectedWallM2 = this.computeSelectedWallSurfaceM2();

    const basket = this.getSurfaceBasket();
    const totalM2 = MathUtils.toFixedFloat(
      basket.reduce((acc, x) => acc + (x.m2 || 0), 0),
      2
    );

    const currentSurface = this.getCurrentSurface();

    return (
      <div>
        <AttributesEditor
          element={element}
          onUpdate={this.updateAttribute}
          attributeFormData={attributesFormData}
          state={appState}
        />

        {selectedWallM2 !== null && (
          <div style={infoRowStyle}>
            <div style={infoLabelStyle}>{translator.t('Surface')}</div>
            <div style={infoValueStyle}>{selectedWallM2} m²</div>
          </div>
        )}

        {selectedAreaM2 !== null && (
          <div style={infoRowStyle}>
            <div style={infoLabelStyle}>{translator.t('Area')}</div>
            <div style={infoValueStyle}>{selectedAreaM2} m²</div>
          </div>
        )}

        {/* Estimator basket box */}
        <div style={estimatorBoxStyle}>
          <div style={estimatorHeaderStyle}>
            <div style={estimatorTitleStyle}>{translator.t('Estimator')}</div>
            <div style={estimatorActionsStyle}>
              <button
                type="button"
                style={currentSurface ? miniBtnStyle : miniBtnDisabledStyle}
                onClick={this.addCurrentSurfaceToBasket}
                disabled={!currentSurface}
                title={
                  currentSurface
                    ? `${currentSurface.label}: ${currentSurface.m2} m²`
                    : 'Select a wall or an area'
                }
              >
                {translator.t('Add')}
              </button>
              <button
                type="button"
                style={basket.length ? miniBtnStyle : miniBtnDisabledStyle}
                onClick={this.clearSurfaceBasket}
                disabled={!basket.length}
              >
                {translator.t('Clear')}
              </button>
            </div>
          </div>

          <div style={estimatorRowStyle}>
            <div style={infoLabelStyle}>{translator.t('Total')}</div>
            <div style={infoValueStyle}>{totalM2} m²</div>
          </div>

          {basket.slice(0, 10).map((it) => (
            <div key={it.id} style={estimatorItemStyle}>
              <div style={{ ...infoLabelStyle, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {it.label}
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5em' }}>
                <div style={infoValueStyle}>{MathUtils.toFixedFloat(it.m2, 2)} m²</div>
                <button
                  type="button"
                  style={removeBtnStyle}
                  onClick={() => this.removeBasketItem(it.id)}
                  title={translator.t('Remove')}
                >
                  ×
                </button>
              </div>
            </div>
          ))}
        </div>

        <div style={attrPorpSeparatorStyle}>
          <div style={headActionStyle}>
            <div
              title={translator.t('Copy')}
              style={iconHeadStyle}
              onClick={(e) => this.copyProperties((element as any).properties)}
            >
              <MdContentCopy />
            </div>
            {appState.clipboardProperties && (appState as any).clipboardProperties.size ? (
              <div
                title={translator.t('Paste')}
                style={iconHeadStyle}
                onClick={(e) => this.pasteProperties()}
              >
                <MdContentPaste />
              </div>
            ) : null}
          </div>
        </div>

        {Object.entries(propertiesFormData).map(([propertyName, data]) => {
          const currentValue = (data as any).currentValue,
            configs = (data as any).configs;

          const { Editor } = CatalogFn.getPropertyType(catalog, configs.type);

          return (
            <Editor
              key={propertyName}
              propertyName={propertyName}
              value={currentValue}
              configs={configs}
              onUpdate={(value: any) => this.updateProperty(propertyName, value)}
              state={appState}
              sourceElement={element}
              internalState={this.state}
            />
          );
        })}
      </div>
    );
  }
}
