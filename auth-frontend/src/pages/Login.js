import React, { useState } from "react";
import axios from "axios";
import { useNavigate, Link } from "react-router-dom";

function Login() {
  const navigate = useNavigate();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleLogin = async (e) => {
    e.preventDefault();
    setMessage("");
    setIsLoading(true);

    try {
      const res = await axios.post("http://localhost:5000/api/auth/login", {
        email,
        password,
      });

      // Stocker le token JWT
      localStorage.setItem("token", res.data.token);

      // Message de succès
      const userName = res.data.user?.name || "Utilisateur";
      const userRole = res.data.user?.role || "user";
      setMessage(`✅ Connecté en tant que ${userName} (${userRole})`);

      // Redirection après 1 seconde
      setTimeout(() => {
        navigate("/multi-sites");
      }, 1000);
    } catch (err) {
      const errorMsg =
        err.response?.data?.message ||
        err.message ||
        "Échec de connexion. Vérifiez vos identifiants.";
      setMessage(`❌ ${errorMsg}`);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="container">
      <div className="row justify-content-center align-items-center min-vh-100">
        <div className="col-md-5 col-sm-8 col-11">
          <div className="card shadow-lg border-0">
            <div className="card-body p-5">
              <h2 className="text-center mb-4 fw-bold text-danger">Connexion</h2>

              <form onSubmit={handleLogin}>
                <div className="mb-3">
                  <input
                    type="email"
                    className="form-control form-control-lg"
                    placeholder="Email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    disabled={isLoading}
                  />
                </div>

                <div className="mb-4">
                  <input
                    type="password"
                    className="form-control form-control-lg"
                    placeholder="Mot de passe"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    disabled={isLoading}
                  />
                </div>

                <button
                  type="submit"
                  className="btn btn-danger btn-lg w-100 fw-bold"
                  disabled={isLoading}
                >
                  {isLoading ? (
                    <>
                      <span className="spinner-border spinner-border-sm me-2" />
                      Connexion en cours...
                    </>
                  ) : (
                    "Se connecter"
                  )}
                </button>
              </form>

              {message && (
                <div
                  className={`alert mt-4 text-center ${
                    message.includes("✅") ? "alert-success" : "alert-danger"
                  }`}
                  role="alert"
                >
                  {message}
                </div>
              )}

              <div className="text-center mt-4">
                <p className="mb-0 text-muted">
                  Pas encore de compte ?{" "}
                  <Link to="/register" className="text-danger fw-bold text-decoration-none">
                    Créer un compte
                  </Link>
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Login;