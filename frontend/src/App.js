import React, { useState, useEffect } from 'react';
import './App.css';

const tg = window.Telegram.WebApp;

// Выносим воронку в константу для удобства
const DEAL_STAGES = [
  "Первичный контакт",
  "Квалификация",
  "Презентация решения",
  "Обработка возражений",
  "Договорённость",
  "Сделка заключена",
];

function App() {
  const [deals, setDeals] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedDeal, setSelectedDeal] = useState(null); // Состояние для выбранной сделки

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
  
  // Функция для обновления статуса
  const handleUpdateStatus = (dealToUpdate) => {
    const currentStageIndex = DEAL_STAGES.indexOf(dealToUpdate.status);
    const nextStage = DEAL_STAGES[currentStageIndex + 1];

    if (!nextStage) {
      alert("Это последний этап!");
      return;
    }
    
    const apiUrl = process.env.REACT_APP_API_URL;
    fetch(`${apiUrl}/api/deals/${dealToUpdate.id}/status`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': `tma ${tg.initData}` },
      body: JSON.stringify({ status: nextStage })
    })
    .then(response => response.json())
    .then(updatedDeal => {
      // Обновляем список сделок и возвращаемся к списку
      fetchDeals();
      setSelectedDeal(null);
    })
    .catch(error => console.error("Ошибка при обновлении статуса:", error));
  };


  // Если сделка не выбрана, показываем список
  if (!selectedDeal) {
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
    disabled={isSubmitting}
  />
  <button type="submit" disabled={isSubmitting}>
    {isSubmitting ? 'Добавление...' : '+ Добавить'}
  </button>
</form>
{error && <p className="error-message">{error}</p>}
        </div>
        {loading ? (
          <p>Загрузка...</p>
        ) : (
          <div className="deals-list">
            {deals.map(deal => (
              <div key={deal.id} className="deal-card" onClick={() => setSelectedDeal(deal)}>
                <h3>{deal.client_name}</h3>
                <p>Статус: {deal.status}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    );
  }

  // Если сделка выбрана, показываем детальный вид
  return (
    <div className="App">
      <div className="header">
        <button onClick={() => setSelectedDeal(null)} className="back-button">
          &larr; Назад к списку
        </button>
        <h1>{selectedDeal.client_name}</h1>
      </div>
      <div className="deal-details">
        <p><strong>Текущий статус:</strong> {selectedDeal.status}</p>
        <hr />
        {/* TODO: Здесь будет чек-лист для текущего этапа */}
        
        {DEAL_STAGES.indexOf(selectedDeal.status) < DEAL_STAGES.length - 1 && (
          <button onClick={() => handleUpdateStatus(selectedDeal)} className="cta-button">
            Перевести на этап: {DEAL_STAGES[DEAL_STAGES.indexOf(selectedDeal.status) + 1]}
          </button>
        )}
      </div>
    </div>
  );
}

export default App;
