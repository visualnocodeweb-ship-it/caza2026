import React, { useState, useEffect } from 'react';
import '../styles/App.css'; // Import global styles
import { fetchErrorLog, fetchPrices } from '../utils/api'; // Import API calls

const DevSection = () => {
  const [showSection, setShowSection] = useState(false);
  const [password, setPassword] = useState('');
  const [loggedIn, setLoggedIn] = useState(false);
  const [errorLog, setErrorLog] = useState([]);
  const [prices, setPrices] = useState([]);
  const [loadingErrors, setLoadingErrors] = useState(false);
  const [loadingPrices, setLoadingPrices] = useState(false);
  const [errorErrors, setErrorErrors] = useState(null);
  const [errorPrices, setErrorPrices] = useState(null);

  useEffect(() => {
    if (loggedIn) {
      const getErrorLog = async () => {
        setLoadingErrors(true);
        try {
          const data = await fetchErrorLog();
          setErrorLog(data);
        } catch (err) {
          setErrorErrors(err.message);
        } finally {
          setLoadingErrors(false);
        }
      };

      const getPrices = async () => {
        setLoadingPrices(true);
        try {
          const data = await fetchPrices();
          setPrices(data);
        } catch (err) {
          setErrorPrices(err.message);
        } finally {
          setLoadingPrices(false);
        }
      };

      getErrorLog();
      getPrices();
    }
  }, [loggedIn]); // Fetch data when loggedIn state changes

  const handleLogin = () => {
    if (password === 'admin123') {
      setLoggedIn(true);
    } else {
      alert('Contraseña incorrecta.');
      setLoggedIn(false);
    }
  };

  // Dynamically get headers for errorLog
  const errorLogHeaders = errorLog.length > 0 ? Object.keys(errorLog[0]) : [];
  // Dynamically get headers for prices
  const pricesHeaders = prices.length > 0 ? Object.keys(prices[0]) : [];

  return (
    <div className="dev-section-container">
      <button onClick={() => setShowSection(!showSection)} className="dev-section-button">
        Desarrollo
      </button>

      {showSection && (
        <div className="dev-section-content">
          <h3>Sección de Desarrollo</h3>
          {!loggedIn ? (
            <div>
              <input
                type="password"
                placeholder="Ingresa la contraseña"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
              <button onClick={handleLogin}>Acceder</button>
            </div>
          ) : (
            <div>
              <p>Acceso concedido.</p>
              
              <h4>Registro de Errores</h4>
              {loadingErrors && <p>Cargando registro de errores...</p>}
              {errorErrors && <p>Error al cargar registro de errores: {errorErrors}</p>}
              {errorLog.length > 0 ? (
                <div style={{ overflowX: 'auto' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                    <thead>
                      <tr>
                        {errorLogHeaders.map((header, index) => (
                          <th key={index} style={{ border: '1px solid #ddd', padding: '8px', textAlign: 'left' }}>
                            {header}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {errorLog.map((logEntry, rowIndex) => (
                        <tr key={rowIndex}>
                          {errorLogHeaders.map((header, colIndex) => (
                            <td key={colIndex} style={{ border: '1px solid #ddd', padding: '8px' }}>
                              {logEntry[header]}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                !loadingErrors && !errorErrors && <p>No hay errores registrados.</p>
              )}

              <h4>Tabla de Precios</h4>
              {loadingPrices && <p>Cargando tabla de precios...</p>}
              {errorPrices && <p>Error al cargar tabla de precios: {errorPrices}</p>}
              {prices.length > 0 ? (
                <div style={{ overflowX: 'auto' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                    <thead>
                      <tr>
                        {pricesHeaders.map((header, index) => (
                          <th key={index} style={{ border: '1px solid #ddd', padding: '8px', textAlign: 'left' }}>
                            {header}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {prices.map((priceItem, rowIndex) => (
                        <tr key={rowIndex}>
                          {pricesHeaders.map((header, colIndex) => (
                            <td key={colIndex} style={{ border: '1px solid #ddd', padding: '8px' }}>
                              {priceItem[header]}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                !loadingPrices && !errorPrices && <p>No hay precios disponibles.</p>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default DevSection;