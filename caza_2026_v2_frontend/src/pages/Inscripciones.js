import React, { useEffect, useState } from 'react';
import { fetchInscripciones, linkData, createPaymentPreference, sendEmailAPI } from '../utils/api';
import '../styles/App.css'; // Import global styles

const RECORDS_PER_PAGE = 10; // Constante para la paginación

const Inscripciones = () => {
  const [inscripciones, setInscripciones] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [expandedStates, setExpandedStates] = useState({}); // To manage expanded state for each record
  const [searchTerm, setSearchTerm] = useState(''); // Estado para el término de búsqueda
  const [linkingData, setLinkingData] = useState(false); // New state for linking data
  const [linkingError, setLinkingError] = useState(null); // New state for linking error
  const [sendingEmail, setSendingEmail] = useState({}); // To manage loading state per email
  // Estados para la paginación
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);
  const [totalRecords, setTotalRecords] = useState(0);

  const getInscripciones = async (page) => { // Acepta 'page' como argumento
    setLoading(true);
    setError(null);
    try {
      const response = await fetchInscripciones(page, RECORDS_PER_PAGE); // Pasa page y limit
      setInscripciones(response.data);
      setTotalRecords(response.total_records);
      setTotalPages(response.total_pages);
      // Initialize all records as collapsed
      const initialExpandedStates = response.data.reduce((acc, _, index) => {
        acc[index] = false;
        return acc;
      }, {});
      setExpandedStates(initialExpandedStates);
    } catch (err) {
      console.error("Error al obtener inscripciones:", err);
      setError('No se pudieron cargar las inscripciones.');
      setInscripciones([]); // Clear inscriptions on error
      setTotalRecords(0);
      setTotalPages(0);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    getInscripciones(currentPage);
  }, [currentPage]); // Dependencia: currentPage

  const toggleExpand = (index) => {
    setExpandedStates(prevStates => ({
      ...prevStates,
      [index]: !prevStates[index]
    }));
  };

  const handleLinkData = async () => {
    setLinkingData(true);
    setLinkingError(null); // Clear previous errors
    try {
      await linkData();
      await getInscripciones(currentPage); // Refetch data after linking, staying on current page
      alert('Datos vinculados y actualizados correctamente.');
    } catch (err) {
      setLinkingError('Error al vincular los datos: ' + err.message);
    } finally {
      setLinkingData(false);
    }
  };

  const handleSendEmail = async (inscripcion, index) => {
    if (!inscripcion.email) {
      alert('No hay dirección de correo para enviar.');
      return;
    }

    setSendingEmail(prevStates => ({ ...prevStates, [index]: true }));
    try {
      const subject = `Contacto desde Panel Caza para ${inscripcion.nombre_establecimiento || 'tu establecimiento'}`;
      const html_content = `
          <p>Estimado/a ${inscripcion.nombre_establecimiento || 'cliente'},</p>
          <p>Nos ponemos en contacto desde Caza 2026. Este es un correo de prueba.</p>
          <p>Saludos cordiales,</p>
          <p>El equipo de Caza 2026</p>
          <br/>
          <p><b>Detalles de la Inscripción:</b></p>
          <ul>
            <li><strong>Nombre de Contacto:</strong> ${inscripcion.nombre_contacto || 'N/A'}</li>
            <li><strong>Razón Social:</strong> ${inscripcion.razon_social || 'N/A'}</li>
            <li><strong>CUIT:</strong> ${inscripcion.cuit || 'N/A'}</li>
            <li><strong>Teléfono:</strong> ${inscripcion.celular || 'N/A'}</li>
            <li><strong>Email:</strong> ${inscripcion.email || 'N/A'}</li>
            <li><strong>Fecha de Inscripción:</strong> ${inscripcion.Fecha || 'N/A'}</li>
            ${inscripcion.pdf_link ? `<li><a href="${inscripcion.pdf_link}" target="_blank" rel="noopener noreferrer">Ver PDF de Inscripción</a></li>` : ''}
          </ul>
      `;

      await sendEmailAPI({
        to_email: inscripcion.email,
        subject: subject,
        html_content: html_content,
      });
      alert(`Correo enviado a ${inscripcion.email} con éxito.`);
    } catch (err) {
      alert(`Error al enviar correo a ${inscripcion.email}: ${err.message}`);
    } finally {
      setSendingEmail(prevStates => ({ ...prevStates, [index]: false }));
    }
  };

  const handleSendPayment = async (inscripcion) => {
    // Temporarily disabled until Mercado Pago credentials are ready
    alert('Funcionalidad de "Enviar Cobro" deshabilitada temporalmente. Por favor, configure las credenciales de Mercado Pago.');
    return;
  };

  // Lógica de filtrado
  const filteredInscripciones = inscripciones.filter(inscripcion =>
    (inscripcion.nombre_establecimiento && inscripcion.nombre_establecimiento.toLowerCase().includes(searchTerm.toLowerCase())) ||
    (inscripcion.razon_social && inscripcion.razon_social.toLowerCase().includes(searchTerm.toLowerCase()))
  );

  if (loading && inscripciones.length === 0) { // Only show full loading if no data is present
    return <p>Cargando inscripciones...</p>;
  }

  if (error) {
    return <p>Error al cargar inscripciones: {error}</p>;
  }

  return (
    <div>
      <h2 style={{ textAlign: 'left', marginBottom: '20px' }}>Inscripciones</h2>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <button
          onClick={handleLinkData}
          disabled={linkingData}
          style={{
            padding: '10px 20px',
            fontSize: '16px',
            fontWeight: 'bold',
            backgroundColor: linkingData ? '#CCCCCC' : '#A8C289', // primaryColor, disabled color
            color: 'white',
            border: 'none',
            borderRadius: '5px',
            cursor: linkingData ? 'not-allowed' : 'pointer',
            transition: 'background-color 0.3s ease',
          }}
        >
          {linkingData ? 'Vinculando...' : 'Vincular Datos'}
        </button>
        <input
          type="text"
          placeholder="Buscar inscripciones por nombre o razón social..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          style={{ width: '70%', padding: '10px', borderRadius: '5px', border: '1px solid #ddd' }}
        />
      </div>
      {linkingError && <p style={{ color: 'red', textAlign: 'center' }}>{linkingError}</p>}
      
      {loading && inscripciones.length > 0 && <p>Actualizando inscripciones...</p>} {/* Show subtle loading when refetching */}

      {filteredInscripciones.length > 0 ? (
        <div className="inscripciones-list">
          {filteredInscripciones.map((inscripcion, index) => (
            <div key={inscripcion.numero_inscripcion || index} className="inscripcion-card"> {/* Using a more stable key */}
              <div className="card-header" onClick={() => toggleExpand(index)}>
                <h3>{inscripcion.nombre_establecimiento || 'Nombre no disponible'}</h3>
                <span className="expand-toggle">{expandedStates[index] ? '▲' : '▼'}</span>
              </div>
              
              {expandedStates[index] && ( // Expanded view
                <div className="card-details">
                  <p><strong>Email:</strong> {inscripcion.email || 'N/A'}</p>
                  <p><strong>Celular:</strong> {inscripcion.celular || 'N/A'}</p>
                  <p><strong>Fecha:</strong> {inscripcion.Fecha || 'N/A'}</p>
                  <div style={{ marginTop: '10px' }}>
                    {inscripcion.pdf_link && (
                      <a href={inscripcion.pdf_link} target="_blank" rel="noopener noreferrer" className="pdf-link-button">
                        Ver PDF
                      </a>
                    )}
                    {inscripcion.email && (
                      <button
                          onClick={() => handleSendEmail(inscripcion, index)}
                          disabled={sendingEmail[index]}
                          style={{
                              marginLeft: '10px',
                              padding: '8px 15px',
                              fontSize: '0.9em',
                              fontWeight: 'bold',
                              backgroundColor: sendingEmail[index] ? '#CCCCCC' : '#4CAF50', // Color verde si no está enviando, gris si está enviando
                              color: 'white',
                              border: 'none',
                              borderRadius: '5px',
                              cursor: sendingEmail[index] ? 'not-allowed' : 'pointer',
                              transition: 'background-color 0.3s ease',
                          }}
                      >
                          {sendingEmail[index] ? 'Enviando...' : 'Enviar Email'}
                      </button>
                    )}
                    {inscripcion.email && (
                      <>
                        <button
                          onClick={() => handleSendPayment(inscripcion)}
                          disabled={true} // Temporarily disabled until Mercado Pago credentials are ready
                          style={{
                            marginLeft: '10px',
                            padding: '8px 15px',
                            fontSize: '0.9em',
                            fontWeight: 'bold',
                            backgroundColor: '#CCCCCC', // Disabled color
                            color: 'white',
                            border: 'none',
                            borderRadius: '5px',
                            cursor: 'not-allowed',
                            transition: 'background-color 0.3s ease',
                          }}
                        >
                          Enviar Cobro
                        </button>
                      </>
                    )}
                  </div>
                </div>
              )}
            </div>
          ))}
          {/* Paginación */}
          <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', marginTop: '20px' }}>
            <button
              onClick={() => setCurrentPage(prev => prev - 1)}
              disabled={currentPage === 1 || loading}
              style={{
                padding: '10px 20px',
                fontSize: '16px',
                fontWeight: 'bold',
                backgroundColor: currentPage === 1 || loading ? '#CCCCCC' : '#007bff',
                color: 'white',
                border: 'none',
                borderRadius: '5px',
                cursor: currentPage === 1 || loading ? 'not-allowed' : 'pointer',
                transition: 'background-color 0.3s ease',
                marginRight: '10px'
              }}
            >
              Anterior
            </button>
            <span>Página {currentPage} de {totalPages} ({totalRecords} registros)</span>
            <button
              onClick={() => setCurrentPage(prev => prev + 1)}
              disabled={currentPage === totalPages || loading}
              style={{
                padding: '10px 20px',
                fontSize: '16px',
                fontWeight: 'bold',
                backgroundColor: currentPage === totalPages || loading ? '#CCCCCC' : '#007bff',
                color: 'white',
                border: 'none',
                borderRadius: '5px',
                cursor: currentPage === totalPages || loading ? 'not-allowed' : 'pointer',
                transition: 'background-color 0.3s ease',
                marginLeft: '10px'
              }}
            >
              Siguiente
            </button>
          </div>
        </div>
      ) : (
        <p>No se encontraron inscripciones que coincidan con la búsqueda.</p>
      )}
    </div>
  );
};

export default Inscripciones;