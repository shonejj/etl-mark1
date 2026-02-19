import { useEffect } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { useAuthStore } from "./context/authStore";
import { getMe } from "./api/auth";
import LoginPage from "./pages/LoginPage";
import { ProtectedRoute, PublicRoute } from "./components/ProtectedRoute";

// Layout
const Layout = ({ children }) => {
  return (
    <div className="flex min-h-screen bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-gray-100">
      <nav className="w-64 bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 p-4">
        <h1 className="text-xl font-bold mb-6 text-blue-600 flex items-center gap-2">
          ⚡ ETL Platform
        </h1>
        <div className="space-y-1">
          <a href="/" className="block px-3 py-2 rounded-md bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 font-medium">Dashboard</a>
          <a href="/pipelines" className="block px-3 py-2 rounded-md hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300">Pipelines</a>
          <a href="/files" className="block px-3 py-2 rounded-md hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300">Files</a>
        </div>
      </nav>
      <main className="flex-1 p-8">
        {children}
      </main>
    </div>
  );
};

const Dashboard = () => {
  const { user, logout } = useAuthStore();
  return (
    <Layout>
      <div className="flex justify-between items-center mb-8">
        <h2 className="text-2xl font-bold">Dashboard</h2>
        <div className="flex items-center gap-4">
          <span className="text-sm text-gray-500">Welcome, {user?.full_name}</span>
          <button onClick={logout} className="text-sm font-medium text-red-600 hover:text-red-500">Logout</button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="p-6 bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700">
          <h3 className="text-gray-500 text-sm font-medium">Total Pipelines</h3>
          <p className="text-3xl font-bold mt-2">12</p>
        </div>
        <div className="p-6 bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700">
          <h3 className="text-gray-500 text-sm font-medium">Active Runs</h3>
          <p className="text-3xl font-bold mt-2 text-blue-600">3</p>
        </div>
        <div className="p-6 bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700">
          <h3 className="text-gray-500 text-sm font-medium">Storage Used</h3>
          <p className="text-3xl font-bold mt-2">1.2 GB</p>
        </div>
      </div>
    </Layout>
  );
};

export default function App() {
  const { isLoading } = useAuthStore();

  useEffect(() => {
    // Check session on mount
    getMe().catch(() => {
      useAuthStore.getState().setLoading(false);
    });
  }, []);

  if (isLoading) {
    return <div className="min-h-screen flex items-center justify-center">Loading...</div>;
  }

  return (
    <BrowserRouter>
      <Routes>
        <Route element={<PublicRoute />}>
          <Route path="/login" element={<LoginPage />} />
        </Route>

        <Route element={<ProtectedRoute />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/pipelines" element={<Layout><div>Pipelines (Coming Soon)</div></Layout>} />
          <Route path="/files" element={<Layout><div>Files (Coming Soon)</div></Layout>} />
        </Route>

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
