import { BrowserRouter, Route, Routes } from "react-router-dom";
import { AuthProvider, Protected } from "./lib/auth";
import AdminUsers from "./pages/AdminUsers";
import CaseDetail from "./pages/CaseDetail";
import Cases from "./pages/Cases";
import Dashboard from "./pages/Dashboard";
import Home from "./pages/Home";
import Login from "./pages/Login";
import Register from "./pages/Register";

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/dashboard" element={<Protected><Dashboard /></Protected>} />
          <Route path="/cases" element={<Protected><Cases /></Protected>} />
          <Route path="/cases/:id" element={<Protected><CaseDetail /></Protected>} />
          <Route path="/admin/users" element={<Protected roles={["ADMIN", "AUDITOR"]}><AdminUsers /></Protected>} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
