import React from 'react';

import { Area, State } from '../../../../models';
import FormTextInput from '../../../style/form-text-input';

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

interface AreaAttributesEditorProps {
  element: Area;
  onUpdate: (name: string, data: string) => void;
  attributeFormData: Area;
  state: State;
  computedAreaM2?: number | null;
  [key: string]: any;
}

export default function AreaAttributesEditor({
  element,
  onUpdate,
  attributeFormData,
  computedAreaM2
}: AreaAttributesEditorProps) {
  const name = attributeFormData.name ?? element.name;
  const areaDisplay = computedAreaM2 === null || computedAreaM2 === undefined ? '' : String(computedAreaM2);

  return (
    <table style={tableStyle}>
      <tbody>
        <tr>
          <td style={firstTdStyle}>Name</td>
          <td>
            <FormTextInput
              value={name}
              onChange={(e) => onUpdate('name', e.target.value)}
              style={inputStyle}
            />
          </td>
        </tr>

        <tr>
          <td style={firstTdStyle}>Area</td>
          <td>
            <div style={measureRowWrapStyle}>
              <FormTextInput value={areaDisplay} onChange={() => {}} style={readOnlyInputStyle} readOnly />
              <div style={unitBoxStyle}>m²</div>
            </div>
          </td>
        </tr>
      </tbody>
    </table>
  );
}
