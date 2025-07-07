import React, { useState, useEffect } from "react";
import "./App.css";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

function App() {
  // Authentication state
  const [user, setUser] = useState(null);
  const [showLoginForm, setShowLoginForm] = useState(false);
  const [showRegisterForm, setShowRegisterForm] = useState(false);
  const [isLogin, setIsLogin] = useState(true);

  // Login form states
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [authError, setAuthError] = useState("");

  // Existing states
  const [goals, setGoals] = useState([]);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [selectedGoal, setSelectedGoal] = useState(null);
  const [goalProgress, setGoalProgress] = useState({});

  // Form states
  const [goalName, setGoalName] = useState("");
  const [targetAmount, setTargetAmount] = useState("");
  const [addMoneyAmount, setAddMoneyAmount] = useState("");
  const [addMoneyDescription, setAddMoneyDescription] = useState("");

  // Check for existing user session on component mount
  useEffect(() => {
    const storedUser = localStorage.getItem("user");
    if (storedUser) {
      setUser(JSON.parse(storedUser));
    }
  }, []);

  // Fetch goals when user is logged in
  useEffect(() => {
    if (user) {
      fetchGoals();
    }
  }, [user]);

  // Authentication functions
  const handleLogin = async (e) => {
    e.preventDefault();
    setAuthError("");
    
    try {
      const response = await axios.post(`${API}/login`, {
        username: username,
        password: password
      });
      
      const userData = response.data;
      setUser(userData);
      localStorage.setItem("user", JSON.stringify(userData));
      
      setUsername("");
      setPassword("");
      setShowLoginForm(false);
    } catch (error) {
      setAuthError(error.response?.data?.detail || "Login failed");
    }
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    setAuthError("");
    
    try {
      const response = await axios.post(`${API}/register`, {
        username: username,
        password: password
      });
      
      const userData = response.data;
      setUser(userData);
      localStorage.setItem("user", JSON.stringify(userData));
      
      setUsername("");
      setPassword("");
      setShowRegisterForm(false);
    } catch (error) {
      setAuthError(error.response?.data?.detail || "Registration failed");
    }
  };

  const handleLogout = () => {
    setUser(null);
    localStorage.removeItem("user");
    setGoals([]);
    setGoalProgress({});
  };

  const fetchGoals = async () => {
    if (!user) return;
    
    try {
      const response = await axios.get(`${API}/goals?user_id=${user.id}`);
      setGoals(response.data);
      
      // Fetch progress for each goal
      for (const goal of response.data) {
        fetchGoalProgress(goal.id);
      }
    } catch (error) {
      console.error("Error fetching goals:", error);
    }
  };

  const fetchGoalProgress = async (goalId) => {
    if (!user) return;
    
    try {
      const response = await axios.get(`${API}/goals/${goalId}/progress?user_id=${user.id}`);
      setGoalProgress(prev => ({
        ...prev,
        [goalId]: response.data
      }));
    } catch (error) {
      console.error("Error fetching goal progress:", error);
    }
  };

  const createGoal = async (e) => {
    e.preventDefault();
    if (!user) return;
    
    try {
      await axios.post(`${API}/goals?user_id=${user.id}`, {
        name: goalName,
        target_amount: parseFloat(targetAmount)
      });
      
      setGoalName("");
      setTargetAmount("");
      setShowCreateForm(false);
      fetchGoals();
    } catch (error) {
      console.error("Error creating goal:", error);
    }
  };

  const addMoney = async (e) => {
    e.preventDefault();
    if (!selectedGoal || !user) return;
    
    try {
      await axios.post(`${API}/transactions?user_id=${user.id}`, {
        goal_id: selectedGoal.id,
        amount: parseFloat(addMoneyAmount),
        description: addMoneyDescription
      });
      
      setAddMoneyAmount("");
      setAddMoneyDescription("");
      setSelectedGoal(null);
      fetchGoals();
    } catch (error) {
      console.error("Error adding money:", error);
    }
  };

  const deleteGoal = async (goalId) => {
    if (!user) return;
    
    if (window.confirm("Are you sure you want to delete this goal?")) {
      try {
        await axios.delete(`${API}/goals/${goalId}?user_id=${user.id}`);
        fetchGoals();
      } catch (error) {
        console.error("Error deleting goal:", error);
      }
    }
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD'
    }).format(amount);
  };

  const formatDays = (days) => {
    if (!days) return "No estimate available";
    if (days < 1) return "Less than 1 day";
    if (days < 7) return `${Math.ceil(days)} days`;
    if (days < 30) return `${Math.ceil(days / 7)} weeks`;
    if (days < 365) return `${Math.ceil(days / 30)} months`;
    return `${Math.ceil(days / 365)} years`;
  };

  // If user is not logged in, show login/register interface
  if (!user) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center">
        <div className="bg-white rounded-xl shadow-lg p-8 w-full max-w-md">
          <div className="text-center mb-8">
            <h1 className="text-3xl font-bold text-gray-800 mb-2">💰 Goal Tracker</h1>
            <p className="text-gray-600">Track your personal savings goals!</p>
          </div>

          {!showLoginForm && !showRegisterForm && (
            <div className="space-y-4">
              <button
                onClick={() => setShowLoginForm(true)}
                className="w-full bg-blue-500 hover:bg-blue-600 text-white py-3 px-6 rounded-lg font-semibold transition-colors duration-200"
              >
                Login
              </button>
              <button
                onClick={() => setShowRegisterForm(true)}
                className="w-full bg-green-500 hover:bg-green-600 text-white py-3 px-6 rounded-lg font-semibold transition-colors duration-200"
              >
                Register
              </button>
            </div>
          )}

          {(showLoginForm || showRegisterForm) && (
            <div>
              <h2 className="text-2xl font-bold mb-6 text-center">
                {showLoginForm ? "Login" : "Register"}
              </h2>
              
              {authError && (
                <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
                  {authError}
                </div>
              )}

              <form onSubmit={showLoginForm ? handleLogin : handleRegister} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Username
                  </label>
                  <input
                    type="text"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    placeholder="Enter your username"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Password
                  </label>
                  <input
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Enter your password"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                    required
                  />
                </div>
                <div className="flex space-x-3">
                  <button
                    type="submit"
                    className="flex-1 bg-blue-500 hover:bg-blue-600 text-white py-2 px-4 rounded-lg font-medium transition-colors duration-200"
                  >
                    {showLoginForm ? "Login" : "Register"}
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setShowLoginForm(false);
                      setShowRegisterForm(false);
                      setAuthError("");
                      setUsername("");
                      setPassword("");
                    }}
                    className="flex-1 bg-gray-300 hover:bg-gray-400 text-gray-700 py-2 px-4 rounded-lg font-medium transition-colors duration-200"
                  >
                    Cancel
                  </button>
                </div>
              </form>
            </div>
          )}
        </div>
      </div>
    );
  }

  // Main app interface (shown when user is logged in)
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="container mx-auto px-4 py-8">
        {/* Header with user info and logout */}
        <div className="flex justify-between items-center mb-8">
          <div className="text-center flex-1">
            <h1 className="text-4xl font-bold text-gray-800 mb-2">💰 Goal Tracker</h1>
            <p className="text-gray-600">Track your savings goals and see when you'll reach them!</p>
          </div>
          <div className="flex items-center space-x-4">
            <div className="text-right">
              <p className="text-sm text-gray-600">Welcome back,</p>
              <p className="font-semibold text-gray-800">{user.username}</p>
            </div>
            <button
              onClick={handleLogout}
              className="bg-red-500 hover:bg-red-600 text-white px-4 py-2 rounded-lg font-medium transition-colors duration-200"
            >
              Logout
            </button>
          </div>
        </div>

        {/* Create Goal Button */}
        <div className="text-center mb-8">
          <button
            onClick={() => setShowCreateForm(true)}
            className="bg-blue-500 hover:bg-blue-600 text-white px-6 py-3 rounded-lg font-semibold shadow-lg transition-all duration-200 transform hover:scale-105"
          >
            + Create New Goal
          </button>
        </div>

        {/* Goals Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {goals.map((goal) => {
            const progress = goalProgress[goal.id];
            const progressPercentage = progress ? Math.min(progress.progress_percentage, 100) : 0;
            
            return (
              <div key={goal.id} className="bg-white rounded-xl shadow-lg p-6 hover:shadow-xl transition-shadow duration-300">
                <div className="flex justify-between items-start mb-4">
                  <h3 className="text-xl font-semibold text-gray-800">{goal.name}</h3>
                  <button
                    onClick={() => deleteGoal(goal.id)}
                    className="text-red-500 hover:text-red-700 text-sm"
                  >
                    Delete
                  </button>
                </div>
                
                {/* Progress Bar */}
                <div className="mb-4">
                  <div className="flex justify-between text-sm text-gray-600 mb-1">
                    <span>{formatCurrency(goal.current_amount)}</span>
                    <span>{formatCurrency(goal.target_amount)}</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-3">
                    <div
                      className="bg-gradient-to-r from-green-400 to-blue-500 h-3 rounded-full transition-all duration-500"
                      style={{ width: `${progressPercentage}%` }}
                    ></div>
                  </div>
                  <p className="text-center text-sm text-gray-600 mt-1">
                    {progressPercentage.toFixed(1)}% Complete
                  </p>
                </div>

                {/* Goal Status */}
                {goal.completed ? (
                  <div className="text-center">
                    <div className="text-green-600 font-semibold mb-2">🎉 Goal Completed!</div>
                    <p className="text-sm text-gray-600">
                      Completed on {new Date(goal.completion_date).toLocaleDateString()}
                    </p>
                  </div>
                ) : (
                  <div className="space-y-2">
                    <div className="text-center">
                      <p className="text-sm text-gray-600">
                        {formatCurrency(progress?.remaining_amount || (goal.target_amount - goal.current_amount))} remaining
                      </p>
                      {progress?.estimated_days_to_completion && (
                        <p className="text-sm font-semibold text-blue-600">
                          Est. {formatDays(progress.estimated_days_to_completion)} to go
                        </p>
                      )}
                      {progress?.average_daily_savings && (
                        <p className="text-xs text-gray-500">
                          Avg. {formatCurrency(progress.average_daily_savings)}/day
                        </p>
                      )}
                    </div>
                    <button
                      onClick={() => setSelectedGoal(goal)}
                      className="w-full bg-green-500 hover:bg-green-600 text-white py-2 px-4 rounded-lg font-medium transition-colors duration-200"
                    >
                      Add Money
                    </button>
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {/* Empty State */}
        {goals.length === 0 && (
          <div className="text-center py-12">
            <div className="text-6xl mb-4">🎯</div>
            <h3 className="text-xl font-semibold text-gray-700 mb-2">No goals yet!</h3>
            <p className="text-gray-600">Create your first savings goal to get started.</p>
          </div>
        )}

        {/* Create Goal Modal */}
        {showCreateForm && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
            <div className="bg-white rounded-xl p-6 w-full max-w-md">
              <h2 className="text-2xl font-bold mb-4">Create New Goal</h2>
              <form onSubmit={createGoal} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    What do you want to buy?
                  </label>
                  <input
                    type="text"
                    value={goalName}
                    onChange={(e) => setGoalName(e.target.value)}
                    placeholder="e.g., New iPhone, Vacation, Car..."
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    How much does it cost?
                  </label>
                  <input
                    type="number"
                    value={targetAmount}
                    onChange={(e) => setTargetAmount(e.target.value)}
                    placeholder="0.00"
                    step="0.01"
                    min="0"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                    required
                  />
                </div>
                <div className="flex space-x-3">
                  <button
                    type="submit"
                    className="flex-1 bg-blue-500 hover:bg-blue-600 text-white py-2 px-4 rounded-lg font-medium transition-colors duration-200"
                  >
                    Create Goal
                  </button>
                  <button
                    type="button"
                    onClick={() => setShowCreateForm(false)}
                    className="flex-1 bg-gray-300 hover:bg-gray-400 text-gray-700 py-2 px-4 rounded-lg font-medium transition-colors duration-200"
                  >
                    Cancel
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Add Money Modal */}
        {selectedGoal && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
            <div className="bg-white rounded-xl p-6 w-full max-w-md">
              <h2 className="text-2xl font-bold mb-4">Add Money to "{selectedGoal.name}"</h2>
              <form onSubmit={addMoney} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Amount
                  </label>
                  <input
                    type="number"
                    value={addMoneyAmount}
                    onChange={(e) => setAddMoneyAmount(e.target.value)}
                    placeholder="0.00"
                    step="0.01"
                    min="0"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500"
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Description (optional)
                  </label>
                  <input
                    type="text"
                    value={addMoneyDescription}
                    onChange={(e) => setAddMoneyDescription(e.target.value)}
                    placeholder="e.g., Weekly savings, Birthday money..."
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500"
                  />
                </div>
                <div className="flex space-x-3">
                  <button
                    type="submit"
                    className="flex-1 bg-green-500 hover:bg-green-600 text-white py-2 px-4 rounded-lg font-medium transition-colors duration-200"
                  >
                    Add Money
                  </button>
                  <button
                    type="button"
                    onClick={() => setSelectedGoal(null)}
                    className="flex-1 bg-gray-300 hover:bg-gray-400 text-gray-700 py-2 px-4 rounded-lg font-medium transition-colors duration-200"
                  >
                    Cancel
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;