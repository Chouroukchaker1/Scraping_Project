import React from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Dashboard from "./pages/Dashboard";
import AppelOffres from "./pages/appel_offres";
import MultiSites from "./pages/mutlisites";
import Boamp from "./pages/boamp";
import Tuneps from "./pages/tuneps";
import TunepsAO from "./pages/tuneps_ao";
import Pnud from "./pages/pnud";
import Haicop from "./pages/haicop";
import Banque from "./pages/banque";
import Armp from "./pages/armp";
import Benin from "./pages/benin";
import Expertise from "./pages/expertise";
import Giz from "./pages/giz";
import Relief from "./pages/relief";
import MediaCongo from "./pages/mediacongo";
import PPDA from "./pages/ppda";
import Niger from "./pages/niger";
import Somalia from "./pages/somalia";

import PrivateRoute from "./components/PrivateRoute";
import Navbar from "./components/Navbar";

// Composant pour rediriger si déjà connecté
const PublicRoute = ({ children }) => {
  const token = localStorage.getItem('token');
  if (token) {
    return <Navigate to="/multi-sites" replace />;
  }
  return children;
};

// Wrapper pour ajouter la navbar aux pages protégées
const ProtectedPage = ({ children }) => {
  return (
    <>
      <Navbar />
      {children}
    </>
  );
};

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Navigate to="/login" replace />} />

        {/* Routes publiques (login/register) - redirigent vers multi-sites si déjà connecté */}
        <Route path="/login" element={<PublicRoute><Login /></PublicRoute>} />
        <Route path="/register" element={<PublicRoute><Register /></PublicRoute>} />

        {/* Routes protégées - nécessitent authentification */}
        {/* DASHBOARD DÉSACTIVÉ - rediriger vers /multi-sites à la place */}
        <Route path="/dashboard" element={<Navigate to="/multi-sites" replace />} />
        <Route path="/tuneps" element={<PrivateRoute><ProtectedPage><Tuneps /></ProtectedPage></PrivateRoute>} />
        <Route path="/pnud" element={<PrivateRoute><ProtectedPage><Pnud /></ProtectedPage></PrivateRoute>} />
        <Route path="/haicop" element={<PrivateRoute><ProtectedPage><Haicop /></ProtectedPage></PrivateRoute>} />
        <Route path="/banque" element={<PrivateRoute><ProtectedPage><Banque /></ProtectedPage></PrivateRoute>} />
        <Route path="/boamp" element={<PrivateRoute><ProtectedPage><Boamp /></ProtectedPage></PrivateRoute>} />
        <Route path="/tuneps_appel-offres" element={<PrivateRoute><ProtectedPage><TunepsAO /></ProtectedPage></PrivateRoute>} />
        <Route path="/armp" element={<PrivateRoute><ProtectedPage><Armp /></ProtectedPage></PrivateRoute>} />
        <Route path="/benin" element={<PrivateRoute><ProtectedPage><Benin /></ProtectedPage></PrivateRoute>} />
        <Route path="/expertise" element={<PrivateRoute><ProtectedPage><Expertise /></ProtectedPage></PrivateRoute>} />
        <Route path="/giz" element={<PrivateRoute><ProtectedPage><Giz /></ProtectedPage></PrivateRoute>} />
        <Route path="/relief" element={<PrivateRoute><ProtectedPage><Relief /></ProtectedPage></PrivateRoute>} />
        <Route path="/mediacongo" element={<PrivateRoute><ProtectedPage><MediaCongo /></ProtectedPage></PrivateRoute>} />
        <Route path="/ppda" element={<PrivateRoute><ProtectedPage><PPDA /></ProtectedPage></PrivateRoute>} />
        <Route path="/niger" element={<PrivateRoute><ProtectedPage><Niger /></ProtectedPage></PrivateRoute>} />
        <Route path="/somalia" element={<PrivateRoute><ProtectedPage><Somalia /></ProtectedPage></PrivateRoute>} />
        <Route path="/multi-sites" element={<PrivateRoute><ProtectedPage><MultiSites /></ProtectedPage></PrivateRoute>} />


        <Route path="*" element={<h2>404 - Page Not Found</h2>} />
      </Routes>
      {/* Note: Le lien Bootstrap devrait être dans index.html ou importé comme CSS module, pas ici */}
      <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet" />
    </BrowserRouter>
  );
}

export default App;
