import { render, screen } from '@testing-library/react';
import App from './App';

jest.mock('react-router-dom', () => ({
  BrowserRouter: ({ children }) => <div>{children}</div>,
  Navigate: () => null,
  NavLink: ({ children }) => <a href="/test">{children}</a>,
  Route: ({ element }) => element,
  Routes: ({ children }) => <div>{children}</div>,
  useNavigate: () => jest.fn(),
}), { virtual: true });

jest.mock('axios', () => ({
  create: jest.fn(() => ({
    get: jest.fn(() => Promise.resolve({ data: [] })),
    post: jest.fn(() => Promise.resolve({ data: {} })),
  })),
  post: jest.fn(() => Promise.resolve({ status: 200 })),
}));

jest.mock('./components/CategoryEditor/CategoryEditor', () => () => <div>Category editor</div>);
jest.mock('./components/DataTable/DataTable', () => () => <div>Statements table</div>);
jest.mock('./components/FileUpload/FileUpload', () => () => <div>File upload</div>);
jest.mock('./components/FilterForm/FilterForm', () => () => <div>Filter form</div>);
jest.mock('./components/AnalyticsDashboard/AnalyticsDashboard', () => () => <div>Analytics dashboard</div>);

test('renders dashboard', () => {
  window.localStorage.setItem('budgetUser', JSON.stringify({ id: 1, username: 'test' }));
  render(<App />);
  expect(screen.getAllByText(/budget app/i)[0]).toBeInTheDocument();
  window.localStorage.removeItem('budgetUser');
});
