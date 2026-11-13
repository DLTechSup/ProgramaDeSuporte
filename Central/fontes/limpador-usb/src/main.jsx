import React from 'react';
import { createRoot } from 'react-dom/client';
import App from './App.jsx';
import { chamar } from './api.js';
import './styles.css';

class Falha extends React.Component {
  state = { erro: null };
  static getDerivedStateFromError(erro) {
    return { erro };
  }
  componentDidCatch(erro) {
    chamar('logRegistrar', { comando: 'interface', resultado: 'FALHA', msg: String(erro && erro.stack) }).catch(() => {});
  }
  render() {
    if (!this.state.erro) return this.props.children;
    return (
      <div className="falha">
        <h2>Algo deu errado na tela</h2>
        <p>O erro foi gravado no log. Você pode tentar continuar.</p>
        <button className="btn primario" onClick={() => this.setState({ erro: null })}>
          Tentar novamente
        </button>
      </div>
    );
  }
}

createRoot(document.getElementById('root')).render(
  <Falha>
    <App />
  </Falha>
);
