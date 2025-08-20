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
  const [newClientName, setNewClientName] = useState(""); // Для поля ввода
  const [error, setError] = useState(""); // Для текста ошибки
  const [isSubmitting, setIsSubmitting] = useState(false); // Для блокировки кнопки
  
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

  // Вот функция, которая важна для формы создания сделки:
  const handleCreateDeal = (e) => {
    e.preventDefault();
    if (!newClientName.trim() || isSubmitting) return;

    setIsSubmitting(true);
    setError("");
    const apiUrl = process.env.REACT_APP_API_URL;

    fetch(`${apiUrl}/api/deals`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': `tma ${tg.initData}` },
      body: JSON.stringify({ client_name: newClientName })
    })
    .then(async response => {
      if (!response.ok) {
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
      setError(error.message);
      console.error("Ошибка при создании сделки:", error);
    })
    .finally(() => {
      setTimeout(() => setIsSubmitting(false), 1000);
    });
  };
  
  // Функция для обновления статуса
  const handleUpdateStatus = (dealToUpdate) => {
const handleToggleChecklistItem = (itemText) => {
    const apiUrl = process.env.REACT_APP_API_URL;
    fetch(`${apiUrl}/api/deals/${selectedDeal.id}/checklist`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': `tma ${tg.initData}` },
      body: JSON.stringify({ text: itemText })
    })
    .then(response => response.json())
    .then(updatedChecklist => {
      // Обновляем состояние локально, чтобы интерфейс сразу отреагировал
      const updatedDeal = { ...selectedDeal, checklist: updatedChecklist };
      setSelectedDeal(updatedDeal);
      
      // Обновляем также и общий список сделок
      setDeals(deals.map(d => d.id === updatedDeal.id ? updatedDeal : d));
    })
    .catch(error => console.error("Ошибка при обновлении пункта чек-листа:", error));
  };
    
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
    <div className="debug-output">
  <h4>Сырые данные сделки:</h4>
  <pre>
    {JSON.stringify(selectedDeal, null, 2)}
  </pre>
</div>
      </div>
      <div className="deal-details">
        <p><strong>Текущий статус:</strong> {selectedDeal.status}</p>
        <hr />
        <div className="checklist">
  <h4>Чек-лист этапа:</h4>
  {selectedDeal.checklist && selectedDeal.checklist.map((item, index) => (
    <div key={index} className="check-item">
      <input 
        type="checkbox"
        id={`item-${index}`}
        checked={item.completed}
        onChange={() => handleToggleChecklistItem(item.text)}
      />
      <label htmlFor={`item-${index}`} className={item.completed ? 'completed' : ''}>
        {item.text}
      </label>
    </div>
  ))}
</div>
        
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
