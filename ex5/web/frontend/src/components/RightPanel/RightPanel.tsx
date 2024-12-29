import { Tabs } from '@mantine/core'
import { Dashboard } from '../Dashboard/Dashboard'
import { TransactionLog } from '../TransactionLog/TransactionLog'
import { NodeData } from '../../types/node'

interface Props {
    nodes: Record<string, NodeData>
}

export const RightPanel = ({ nodes }: Props) => {
    return (
        <div className="h-full bg-white rounded-lg shadow-lg">
            <Tabs defaultValue="status" styles={{
                root: { height: '100%', display: 'flex', flexDirection: 'column' },
                panel: { flex: 1, overflowY: 'auto' },
                list: { borderBottom: '1px solid #e5e7eb' }
            }}>
                <Tabs.List>
                    <Tabs.Tab value="status">Node Status</Tabs.Tab>
                    <Tabs.Tab value="transactions">Transactions</Tabs.Tab>
                </Tabs.List>

                <Tabs.Panel value="status" pt="xs">
                    <div className="p-4">
                        <Dashboard nodes={nodes} />
                    </div>
                </Tabs.Panel>
                <Tabs.Panel value="transactions" pt="xs">
                    <div className="p-4">
                        <TransactionLog nodes={nodes} />
                    </div>
                </Tabs.Panel>
            </Tabs>
        </div>
    )
}