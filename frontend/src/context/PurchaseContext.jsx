import React, { createContext, useContext, useState, useEffect } from 'react';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;

// Purchase system is now ENABLED with Stripe
const STRIPE_INTEGRATION_COMPLETE = true;

const PurchaseContext = createContext();

export const PurchaseProvider = ({ children }) => {
  const [purchasesEnabled, setPurchasesEnabled] = useState(STRIPE_INTEGRATION_COMPLETE);
  const [stripeConfigured, setStripeConfigured] = useState(false);

  useEffect(() => {
    // Check if Stripe is configured
    checkStripeStatus();
  }, []);

  const checkStripeStatus = async () => {
    try {
      const res = await fetch(`${API}/api/purchase/stripe-status`);
      if (res.ok) {
        const data = await res.json();
        setStripeConfigured(data.configured);
        setPurchasesEnabled(data.purchases_enabled);
      }
    } catch (err) {
      console.log('Stripe status check unavailable');
      setStripeConfigured(false);
      setPurchasesEnabled(STRIPE_INTEGRATION_COMPLETE);
    }
  };

  const attemptPurchase = (itemName, callback) => {
    if (!purchasesEnabled) {
      toast.error(
        "Purchases are temporarily unavailable", 
        { 
          description: "Please try again later.",
          duration: 5000
        }
      );
      return false;
    }
    
    if (callback) callback();
    return true;
  };

  const canPurchase = () => purchasesEnabled;

  const getPurchaseMessage = () => {
    if (!stripeConfigured) {
      return "Payment system is being configured. Please try again later.";
    }
    return null;
  };

  return (
    <PurchaseContext.Provider value={{ 
      purchasesEnabled, 
      attemptPurchase, 
      canPurchase,
      getPurchaseMessage,
      stripeConfigured,
      STRIPE_INTEGRATION_COMPLETE
    }}>
      {children}
    </PurchaseContext.Provider>
  );
};

export const usePurchase = () => {
  const context = useContext(PurchaseContext);
  if (!context) {
    throw new Error('usePurchase must be used within a PurchaseProvider');
  }
  return context;
};

// HOC to wrap purchase buttons
export const PurchaseButton = ({ 
  children, 
  onClick, 
  disabled = false, 
  className = "",
  itemName = "item",
  ...props 
}) => {
  const { attemptPurchase, canPurchase } = usePurchase();
  const isPurchaseDisabled = !canPurchase();

  const handleClick = (e) => {
    if (attemptPurchase(itemName, onClick)) {
      // Purchase allowed - onClick already called in attemptPurchase
    }
  };

  return (
    <button
      onClick={handleClick}
      disabled={disabled || isPurchaseDisabled}
      className={`${className} ${isPurchaseDisabled ? 'opacity-50 cursor-not-allowed' : ''}`}
      title={isPurchaseDisabled ? "Purchases temporarily unavailable" : ""}
      {...props}
    >
      {children}
    </button>
  );
};

export default PurchaseContext;
