import React from 'react';

type SimpleTableProps = {
  // Define any props here if needed, for example:
  // data: Array<{ id: number; name: string; value: string }>;
};

const SimpleTable: React.FC<SimpleTableProps> = (props) => {
  // Example static data, replace or extend according to your needs
  const data = [
    { type: "Power", source: 'f.power_out', target: 'p.power_in' },
    { type: "Signal", source: 'b.gnd', target: 'a.gnd' },
    { type: "I2C", source: 'a.i2c', target: 'c.d.i2c' },
  ];

  return (
    <div style={{backgroundColor: 'lightgray', border: '2px solid grey', margin: '10px', padding: '10px', borderRadius: '10px'}}>
        <div style={{textAlign: 'center'}}> Link inspection pane</div>
        <table className='table'>
            <thead>
                <tr>
                    <th>Type</th>
                    <th style={{ textAlign: 'right', width: '100px' }}>Source</th>
                    <th>  ~  </th>
                    <th style={{ textAlign: 'left', width: '100px' }}>Target</th>
                </tr>
            </thead>
            <tbody>
                {data.map((item) => (
                <tr key={item.id}>
                    <td style={{ textAlign: 'center', width: '100px' }}>{item.type}</td>
                    <td style={{ textAlign: 'right', width: '100px' }}>{item.source}</td>
                    <td>  ~  </td>
                    <td style={{ textAlign: 'left', width: '100px' }}>{item.target}</td>
                </tr>
                ))}
            </tbody>
        </table>
    </div>
  );
};

export default SimpleTable;
