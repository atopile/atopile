import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Layout } from '@/components';
import { Dashboard, Pipelines } from '@/pages';

function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/pipelines" element={<Pipelines />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
}

export default App;
