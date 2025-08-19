import React, { useState, useEffect } from 'react';
import './App.css';

// Получаем объект Telegram Web App
const tg = window.Telegram.WebApp;

function App() {
  const [deals, setDeals] = useState([]);
  const [loading, setLoading] = useState(true);
  const [newClientName, setNewClientName] = useState(""); // Состояние для имени в форме

  // Функция для загрузки сделок с бэкенда
  const fetchDeals = () => {
    setLoading(true);
    const apiUrl = process.env.REACT_APP_API_URL;
    
    fetch(`${apiUrl}/api/deals`, {
      headers: {
        // Отправляем данные авторизации, чтобы бэкенд знал, кто мы
        'Authorization': `tma ${tg.initData}`
      }
    })
      .then(response => response.json())
      .then(data => {
        setDeals(data);
        setLoading(false);
      })
      .catch(error => {
        console.error("Ошибка при загрузке сделок:", error);
        setLoading(false);
      });
  };

  // Вызываем загрузку сделок один раз при старте
  useEffect(() => {
    tg.ready(); // Сообщаем Telegram, что приложение готово
    fetchDeals();
  }, []);

  // Функция для создания новой сделки
  const handleCreateDeal = (e) => {
    e.preventDefault(); // Предотвращаем стандартное поведение формы
    if (!newClientName.trim()) return; // Не создаем сделку с пустым именем

    const apiUrl = process.env.REACT_APP_API_URL;

    fetch(`${apiUrl}/api/deals`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `tma ${tg.initData}`
      },
      body: JSON.stringify({ client_name: newClientName })
    })
    .then(response => response.json())
    .then(newDeal => {
      // Добавляем новую сделку в начало списка
      setDeals(prevDeals => [newDeal, ...prevDeals]);
      setNewClientName(""); // Очищаем поле ввода
    })
    .catch(error => console.error("Ошибка при создании сделки:", error));
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
          />
          <button type="submit">+ Добавить</button>
        </form>
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
