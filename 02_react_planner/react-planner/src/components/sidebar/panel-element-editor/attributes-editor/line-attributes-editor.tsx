import React, { useContext, useMemo } from 'react';

import convert from 'convert-units';

import { PropertyLengthMeasure } from '../../../../catalog/properties/export';
import { Line, State } from '../../../../models';
import ReactPlannerContext from '../../../../react-planner-context';
import { LineAttributes } from '../../../../types';
import { FormTextInput } from '../../../style/export';

const tableStyle = { width: '100%' } as const;
const firstTdStyle = { width: '6em' } as const;
const inputStyle = { textAlign: 'left' } as const;

const measureRowWrapStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'stretch',
  width: '100%'
};

const unitBoxStyle: React.CSSProperties = {
  width: '4.2em',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  border: '1px solid #cfcfcf',
  borderLeft: 'none',
  background: '#f5f5f5',
  color: '#333',
  fontSize: '0.95em'
};

const readOnlyInputStyle: React.CSSProperties = {
  ...inputStyle,
  borderRight: 'none'
};

interface LineAttributesEditorProps {
  element: Line;
  onUpdate: (key: string, value: any) => void;
  attributeFormData: LineAttributes;
  state: State;
  [key: string]: any;
}

export default function LineAttributesEditor({
  element,
  onUpdate,
  attributeFormData,
  state
}: LineAttributesEditorProps) {
  const { translator, catalog } = useContext(ReactPlannerContext);

  const name = attributeFormData.name || element.name;
  const lineLength = attributeFormData.lineLength || null;

  const wallSurfaceM2 = useMemo(() => {
    try {
      const lenU = Number(lineLength?.length ?? 0);
      const hU = Number(element.properties?.height?.length ?? 0);
      if (!isFinite(lenU) || !isFinite(hU) || lenU <= 0 || hU <= 0) return null;

      const lenM = convert(lenU).from(catalog.unit).to('m');
      const hM = convert(hU).from(catalog.unit).to('m');

      const m2 = lenM * hM;
      if (!isFinite(m2) || m2 <= 0) return null;

      return Math.round(m2 * 100) / 100;
    } catch {
      return null;
    }
  }, [lineLength, element.properties, catalog.unit]);

  const wallSurfaceDisplay = wallSurfaceM2 === null ? '' : String(wallSurfaceM2);

  return (
    <div>
      <table style={tableStyle}>
        <tbody>
          <tr>
            <td style={firstTdStyle}>{translator.t('Name')}</td>
            <td>
              <FormTextInput
                value={wallSurfaceDisplay ? `${wallSurfaceDisplay} m²` : ''}
                onChange={() => {}}
                style={inputStyle}
                readOnly
              />
            </td>
          </tr>

          <tr>
            <td style={firstTdStyle}>{translator.t('Surface')}</td>
            <td>
              
            </td>
          </tr>
        </tbody>
      </table>

      <PropertyLengthMeasure
        value={lineLength}
        onUpdate={(mapped) => onUpdate('lineLength', mapped)}
        configs={{
          label: translator.t('Length'),
          min: 0,
          max: Infinity,
          precision: 2
        }}
        state={state}
      />
    </div>
  );
}
