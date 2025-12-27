import React, { useEffect, useState } from "react";
import axios from "axios";

function Protected() {
  const [data, setData] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    const token = localStorage.getItem("token");
    if (!token) {
      setError("No token found. Please login.");
      return;
    }

    axios.get("http://localhost:5000/api/protected", {
      headers: { Authorization: `Bearer ${token}` }
    })
      .then(res => setData(res.data.message))
      .catch(err => setError(err.response?.data?.message || "Access denied"));
  }, []);

  return (
    <div style={{ padding: "2rem" }}>
      <h2>Protected Page</h2>
      {data && <p>{data}</p>}
      {error && <p style={{ color: "red" }}>{error}</p>}
    </div>
  );
}

export default Protected;
