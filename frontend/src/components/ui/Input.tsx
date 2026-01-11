import React from 'react';

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  helperText?: string;
}

export const Input: React.FC<InputProps> = ({
  label,
  error,
  helperText,
  className = '',
  ...props
}) => {
  return (
    <div className="w-full">
      {label && (
        <label className="block text-apple-body font-medium mb-2 text-text-primary">
          {label}
        </label>
      )}
      <input
        className={`input-apple ${error ? 'border-apple-red' : ''} ${className}`}
        {...props}
      />
      {error && (
        <p className="mt-1 text-sm text-apple-red">{error}</p>
      )}
      {helperText && !error && (
        <p className="mt-1 text-sm text-text-secondary">{helperText}</p>
      )}
    </div>
  );
};

export default Input;

