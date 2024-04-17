// @ts-nocheck
// Glad we are using ts huh?
import React from 'react';

type SimpleTableProps = {
    source: string;
    target: string;
    data: Array<{ type: string; instance_of: string; source: string; target: string }>;
};

const SimpleTable: React.FC<SimpleTableProps> = ({source, target, data}) => {

    return (
        <div style={{backgroundColor: 'lightgray', border: '2px solid grey', margin: '10px', padding: '10px', borderRadius: '10px'}}>
            <div style={{textAlign: 'center'}}> Link inspection pane</div>
            <table className='table'>
                <thead>
                    <tr>
                        <th style={{ textAlign: 'center', width: '100px' }}>Type</th>
                        <th style={{ textAlign: 'center', width: '100px' }}>Instance of</th>
                        <th style={{ textAlign: 'right', width: '100px' }}>{source}</th>
                        <th>  ~  </th>
                        <th style={{ textAlign: 'left', width: '100px' }}>{target}</th>
                    </tr>
                </thead>
                <tbody>
                    {data.map((item) => (
                    <tr key={item.id}>
                        <td style={{ textAlign: 'center', width: '100px' }}>{item.type}</td>
                        <td style={{ textAlign: 'center', width: '100px' }}>{item.instance_of}</td>
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
