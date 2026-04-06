import { useState } from 'react';
import './App.css';

import HomeScreen      from './screens/HomeScreen';
import AddScreen       from './screens/AddScreen';
import UseScreen       from './screens/UseScreen';
import RemoveScreen    from './screens/RemoveScreen';
import InventoryScreen from './screens/InventoryScreen';
import RecipesScreen   from './screens/RecipesScreen';

export default function App() {
  const [screen, setScreen] = useState('home');

  const goHome = () => setScreen('home');

  const screens = {
    home:      <HomeScreen      onNavigate={setScreen} />,
    add:       <AddScreen       onBack={goHome} />,
    use:       <UseScreen       onBack={goHome} />,
    remove:    <RemoveScreen    onBack={goHome} />,
    inventory: <InventoryScreen onBack={goHome} />,
    recipes:   <RecipesScreen   onBack={goHome} />,
  };

  return (
    <div className="app">
      <header className="header">
        <div className="header-logo">Smart Pantry</div>
        <div className="header-status">
          <div className="status-dot" />
          System Online
        </div>
      </header>
      {screens[screen] ?? <HomeScreen onNavigate={setScreen} />}
    </div>
  );
}