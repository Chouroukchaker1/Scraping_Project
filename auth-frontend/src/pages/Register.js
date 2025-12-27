import React, { useState } from "react";
import axios from "axios";
import { useNavigate, Link } from "react-router-dom";

function Register() {
  const navigate = useNavigate();

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState("");
  const [errors, setErrors] = useState({});
  const [isLoading, setIsLoading] = useState(false);

  const validateForm = () => {
    const newErrors = {};

    if (!name.trim()) newErrors.name = "Le nom est requis";
    if (!email.trim()) newErrors.email = "L'email est requis";
    else if (!/^[\w-.]+@([\w-]+\.)+[\w-]{2,4}$/.test(email))
      newErrors.email = "Email invalide";

    if (!password) newErrors.password = "Le mot de passe est requis";
    else if (password.length < 6)
      newErrors.password = "Minimum 6 caractères";

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validateForm()) return;

    setIsLoading(true);
    setMessage("");
    setErrors({});

    try {
      await axios.post("http://localhost:5000/api/auth/register", {
        name: name.trim(),
        email: email.trim(),
        password,
      });

      setMessage("✅ Inscription réussie ! Redirection vers la connexion...");
      setName("");
      setEmail("");
      setPassword("");

      setTimeout(() => {
        navigate("/login");
      }, 2000);
    } catch (err) {
      const errorMsg =
        err.response?.data?.message ||
        "Erreur lors de l'inscription. Essayez un autre email.";
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
              <h2 className="text-center mb-4 fw-bold text-danger">Inscription</h2>

              <form onSubmit={handleSubmit}>
                <div className="mb-3">
                  <input
                    type="text"
                    className={`form-control form-control-lg ${errors.name ? "is-invalid" : ""}`}
                    placeholder="Nom complet"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    disabled={isLoading}
                  />
                  {errors.name && <div className="invalid-feedback">{errors.name}</div>}
                </div>

                <div className="mb-3">
                  <input
                    type="email"
                    className={`form-control form-control-lg ${errors.email ? "is-invalid" : ""}`}
                    placeholder="Email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    disabled={isLoading}
                  />
                  {errors.email && <div className="invalid-feedback">{errors.email}</div>}
                </div>

                <div className="mb-4">
                  <input
                    type="password"
                    className={`form-control form-control-lg ${errors.password ? "is-invalid" : ""}`}
                    placeholder="Mot de passe (min. 6 caractères)"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    disabled={isLoading}
                  />
                  {errors.password && <div className="invalid-feedback">{errors.password}</div>}
                </div>

                <button
                  type="submit"
                  className="btn btn-danger btn-lg w-100 fw-bold"
                  disabled={isLoading}
                >
                  {isLoading ? (
                    <>
                      <span className="spinner-border spinner-border-sm me-2" />
                      Inscription en cours...
                    </>
                  ) : (
                    "S'inscrire"
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
                  Déjà un compte ?{" "}
                  <Link to="/login" className="text-danger fw-bold text-decoration-none">
                    Se connecter
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

export default Register;