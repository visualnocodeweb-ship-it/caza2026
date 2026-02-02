import React from 'react';
import { NavLink } from 'react-router-dom';
import '../styles/App.css'; // Import global styles

const Navbar = () => {
  return (
    <nav className="navbar">
      <NavLink to="/inscripciones" className={({ isActive }) => "nav-item" + (isActive ? " active" : "")}>
        Inscripciones
      </NavLink>
      <NavLink to="/permiso-caza" className={({ isActive }) => "nav-item" + (isActive ? " active" : "")}>
        Permiso de Caza
      </NavLink>
      <NavLink to="/dashboard" className={({ isActive }) => "nav-item" + (isActive ? " active" : "")}>
        Dashboard
      </NavLink>
    </nav>
  );
};

export default Navbar;