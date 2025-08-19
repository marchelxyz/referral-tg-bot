import React, { useState, useEffect } from 'react';
import './App.css';

function App() {
  const [deals, setDeals] = useState([]); // Состояние для хранения списка сделок
  const [loading, setLoading] = useState(true); // Состояние для отслеживания загрузки
  
  // Этот хук выполнится один раз при загрузке компонента
  useEffect(() => {
    // Получаем URL нашего API из переменных окружения Vercel
    const apiUrl = process.env.REACT_APP_API_URL;

    // Запрашиваем данные с бэкенда
    fetch(`${apiUrl}/api/deals`)
      .then(response => response.json())
      .then(data => {
        setDeals(data); // Сохраняем полученные сделки
        setLoading(false); // Убираем индикатор загрузки
      })
      .catch(error => {
        console.error("Ошибка при загрузке сделок:", error);
        setLoading(false); // Убираем индикатор загрузки даже при ошибке
      });
  }, []); // Пустой массив зависимостей означает "выполнить только один раз"

  return (
    <div className="App">
      <header className="App-header">
        <h1>Мои сделки</h1>
        {loading ? (
          <p>Загрузка...</p>
        ) : (
          <div className="deals-list">
            {deals.map(deal => (
              <div key={deal.id} className="deal-card">
                <h3>{deal.client_name}</h3>
                <p>Статус: {deal.status}</p>
              </div>
            ))}
          </div>
        )}
      </header>
    </div>
  );
}

export default App;
