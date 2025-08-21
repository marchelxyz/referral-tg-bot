import React, { useState, useEffect } from 'react';
import './App.css';

const tg = window.Telegram.WebApp;

const DEAL_STAGES = ["Первичный контакт", "Квалификация", "Презентация решения", "Обработка возражений", "Договорённость", "Сделка заключена"];

function App() {
  const [deals, setDeals] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedDeal, setSelectedDeal] = useState(null);
  const [debugInfo, setDebugInfo] = useState(null); // НОВОЕ СОСТОЯНИЕ ДЛЯ ОТЛАДКИ

  // ... (остальные состояния useState остаются без изменений)
  const [newClientName, setNewClientName] = useState("");
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const fetchDeals = () => { /* ... код без изменений ... */ };
  useEffect(() => { tg.ready(); fetchDeals(); }, []);
  const handleCreateDeal = (e) => { /* ... код без изменений ... */ };
  const handleUpdateStatus = (dealToUpdate) => { /* ... код без изменений ... */ };


  // ОБНОВЛЕННАЯ ФУНКЦИЯ ДЛЯ ОБРАБОТКИ ЧЕК-ЛИСТА
  const handleToggleChecklistItem = (itemText) => {
    setDebugInfo("Отправка запроса..."); // Показываем, что запрос начался
    const apiUrl = process.env.REACT_APP_API_URL;
    
    fetch(`${apiUrl}/api/deals/${selectedDeal.id}/checklist`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': `tma ${tg.initData}` },
      body: JSON.stringify({ text: itemText })
    })
    .then(async response => {
      if (!response.ok) {
        const errorText = await response.text();
        // Записываем ошибку в отладочный блок
        setDebugInfo({ status: response.status, error: errorText });
        throw new Error(errorText);
      }
      return response.json();
    })
    .then(updatedChecklist => {
      // Записываем успешный ответ в отладочный блок
      setDebugInfo(updatedChecklist);
      
      const updatedDeal = { ...selectedDeal, checklist: updatedChecklist };
      setSelectedDeal(updatedDeal);
      setDeals(deals.map(d => d.id === updatedDeal.id ? updatedDeal : d));
    })
    .catch(error => {
      // Если ошибка на уровне сети, тоже записываем
      setDebugInfo({ error: error.message });
      console.error("Ошибка при обновлении пункта чек-листа:", error);
    });
  };

  if (selectedDeal) {
    return (
      <div className="App">
        <div className="header">
          <button onClick={() => { setSelectedDeal(null); setDebugInfo(null); }} className="back-button">
            &larr; Назад к списку
          </button>
          <h1>{selectedDeal.client_name}</h1>
        </div>
        <div className="deal-details">
            {/* ... код отображения статуса и чек-листа ... */}
            <div className="checklist">
              <h4>Чек-лист этапа:</h4>
              {selectedDeal.checklist && selectedDeal.checklist.map((item, index) => (
                <div key={index} className="check-item">
                  <input type="checkbox" id={`item-${index}`} checked={item.completed} onChange={() => handleToggleChecklistItem(item.text)} />
                  <label htmlFor={`item-${index}`} className={item.completed ? 'completed' : ''}>{item.text}</label>
                </div>
              ))}
            </div>
            {/* ... кнопка смены этапа ... */}
        </div>

        {/* НОВЫЙ БЛОК ДЛЯ ВЫВОДА ОТЛАДОЧНОЙ ИНФОРМАЦИИ */}
        {debugInfo && (
          <div className="debug-output">
            <h4>Отладочная информация:</h4>
            <pre>{JSON.stringify(debugInfo, null, 2)}</pre>
          </div>
        )}
      </div>
    );
  }

  // Основной вид списка (без изменений)
  return ( <div className="App">{/* ... */}</div> );
}

export default App;
