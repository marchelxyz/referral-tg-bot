import React, { useState, useEffect } from 'react';
import './App.css';

const tg = window.Telegram.WebApp;

function App() {
  const [deals, setDeals] = useState([]);
  const [loading, setLoading] = useState(true);
  const [newClientName, setNewClientName] = useState("");
  const [error, setError] = useState(""); // Состояние для текста ошибки
  const [isSubmitting, setIsSubmitting] = useState(false); // Состояние для блокировки кнопки

  const fetchDeals = () => {
    // ... (код этой функции не изменился)
    setLoading(true);
    const apiUrl = process.env.REACT_APP_API_URL;
    fetch(`${apiUrl}/api/deals`, { headers: { 'Authorization': `tma ${tg.initData}` } })
      .then(response => response.json())
      .then(data => { setDeals(data); setLoading(false); })
      .catch(error => { console.error("Ошибка при загрузке сделок:", error); setLoading(false); });
  };

  useEffect(() => {
    tg.ready();
    fetchDeals();
  }, []);

  const handleCreateDeal = (e) => {
    e.preventDefault();
    if (!newClientName.trim() || isSubmitting) return;

    setIsSubmitting(true); // Блокируем кнопку
    setError(""); // Сбрасываем старую ошибку
    const apiUrl = process.env.REACT_APP_API_URL;

    fetch(`${apiUrl}/api/deals`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': `tma ${tg.initData}` },
      body: JSON.stringify({ client_name: newClientName })
    })
    .then(async response => {
      if (!response.ok) {
        // Если сервер ответил ошибкой, считываем ее текст
        const errorText = await response.text();
        throw new Error(errorText);
      }
      return response.json();
    })
    .then(newDeal => {
      setDeals(prevDeals => [newDeal, ...prevDeals]);
      setNewClientName("");
    })
    .catch(error => {
      // Показываем ошибку пользователю
      setError(error.message);
      console.error("Ошибка при создании сделки:", error);
    })
    .finally(() => {
      // Разблокируем кнопку через секунду в любом случае
      setTimeout(() => setIsSubmitting(false), 1000);
    });
  };

  return (
    <div className="App">
      <div className="header">
        <h1>Мои сделки</h1>
        <form onSubmit={handleCreateDeal} className="deal-form">
          <input
            type="text"
            value={newClientName}
            onChange={(e) => setNewClientName(e.target.value)}
            placeholder="Имя нового клиента"
            disabled={isSubmitting} // Кнопка неактивна во время отправки
          />
          <button type="submit" disabled={isSubmitting}>
            {isSubmitting ? 'Добавление...' : '+ Добавить'}
          </button>
        </form>
        {/* Отображение ошибки */}
        {error && <p className="error-message">{error}</p>}
      </div>

      {loading ? (
        <p>Загрузка...</p>
      ) : (
        <div className="deals-list">
          {deals.length > 0 ? (
            deals.map(deal => (
              <div key={deal.id} className="deal-card">
                <h3>{deal.client_name}</h3>
                <p>Статус: {deal.status}</p>
              </div>
            ))
          ) : (
            <p>У вас пока нет сделок. Создайте первую!</p>
          )}
        </div>
      )}
    </div>
  );
}

export default App;
