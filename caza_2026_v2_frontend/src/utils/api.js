// src/utils/api.js
// This file will contain functions to interact with your backend API

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000/api'; // Example backend URL

export const fetchInscripciones = async (page = 1, limit = 10) => {
  try {
    const response = await fetch(`${API_BASE_URL}/inscripciones?page=${page}&limit=${limit}`);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    const data = await response.json();
    return data;
  } catch (error) {
    console.error("Error fetching inscripciones:", error);
    return { data: [], total_records: 0, page: 1, limit: 10, total_pages: 0 }; // Return a structured empty response
  }
};

export const fetchErrorLog = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/error-log`);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    const data = await response.json();
    return data;
  } catch (error) {
    console.error("Error fetching error log:", error);
    return [];
  }
};

export const fetchPrices = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/prices`);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    const data = await response.json();
    return data;
  } catch (error) {
    console.error("Error fetching prices:", error);
    return [];
  }
};

// Add more API functions as needed

export const linkData = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/link-data`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      // body: JSON.stringify({ /* any data you might need to send */ }),
    });
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    const data = await response.json();
    return data;
  } catch (error) {
    console.error("Error linking data:", error);
    throw error; // Re-throw to be handled by the component
  }
};

export const createPaymentPreference = async (paymentDetails) => {
  try {
    const response = await fetch(`${API_BASE_URL}/create-payment-preference`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(paymentDetails),
    });
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
    }
    const data = await response.json();
    return data;
  } catch (error) {
    console.error("Error creating payment preference:", error);
    throw error;
  }
};

export const simulatePayment = async (paymentDetails) => {
  try {
    const response = await fetch(`${API_BASE_URL}/simulate-payment`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(paymentDetails),
    });
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
    }
    const data = await response.json();
    return data;
  } catch (error) {
    console.error("Error simulating payment:", error);
    throw error;
  }
};

export const sendEmailAPI = async (emailData) => {
  try {
    const response = await fetch(`${API_BASE_URL}/send-email`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(emailData),
    });
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
    }
    const data = await response.json();
    return data;
  } catch (error) {
    console.error("Error sending email:", error);
    throw error;
  }
};

