import React from 'react';
import './App.css';

function App() {
  // Получаем данные о приложении Telegram
  const tg = window.Telegram.WebApp;

  return (
    <div className="App">
      <header className="App-header">
        <h1>Привет, это наше Mini App!</h1>
        {/* Выводим данные пользователя для проверки */}
        {tg.initDataUnsafe?.user && (
          <p>
            Пользователь: {tg.initDataUnsafe.user.first_name}
          </p>
        )}
      </header>
    </div>
  );
}

export default App;
