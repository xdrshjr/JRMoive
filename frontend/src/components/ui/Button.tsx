import React from 'react';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger';
  size?: 'sm' | 'md' | 'lg';
  loading?: boolean;
  as?: 'button' | 'span';
  children: React.ReactNode;
}

export const Button: React.FC<ButtonProps> = ({
  variant = 'primary',
  size = 'md',
  loading = false,
  disabled,
  as = 'button',
  children,
  className = '',
  ...props
}) => {
  const baseClasses = 'btn-apple transition-apple font-semibold inline-flex items-center justify-center';
  
  const variantClasses = {
    primary: 'btn-apple-primary',
    secondary: 'btn-apple-secondary',
    danger: 'bg-apple-red hover:bg-red-600 text-white',
  };
  
  const sizeClasses = {
    sm: 'px-4 py-2 text-sm',
    md: 'px-6 py-3 text-base',
    lg: 'px-8 py-4 text-lg',
  };
  
  const combinedClasses = [
    baseClasses,
    variantClasses[variant],
    sizeClasses[size],
    (disabled || loading) && 'opacity-50 cursor-not-allowed',
    className,
  ]
    .filter(Boolean)
    .join(' ');

  const content = loading ? (
    <div className="flex items-center gap-2">
      <div className="spinner-apple" />
      <span>Loading...</span>
    </div>
  ) : (
    children
  );

  if (as === 'span') {
    return (
      <span className={combinedClasses} {...(props as any)}>
        {content}
      </span>
    );
  }

  return (
    <button
      className={combinedClasses}
      disabled={disabled || loading}
      {...props}
    >
      {content}
    </button>
  );
};

export default Button;

