import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { ThemeProvider, createTheme, CssBaseline } from '@mui/material';
import MainLayout from './layouts/MainLayout';
import DashboardPage from './pages/DashboardPage';
import DeploymentsPage from './pages/DeploymentsPage';
import InferencePage from './pages/InferencePage';
import BenchmarksPage from './pages/BenchmarksPage';

// Create a theme instance
const theme = createTheme({
  palette: {
    primary: {
      main: '#1976d2',
    },
    secondary: {
      main: '#dc004e',
    },
  },
});

function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Router>
        <Routes>
          <Route path="/" element={<MainLayout />}>
            <Route index element={<DashboardPage />} />
            <Route path="deployments" element={<DeploymentsPage />} />
            <Route path="inference" element={<InferencePage />} />
            <Route path="benchmarks" element={<BenchmarksPage />} />
            {/* Add more routes as needed */}
            <Route path="*" element={<DashboardPage />} />
          </Route>
        </Routes>
      </Router>
    </ThemeProvider>
  );
}

export default App;