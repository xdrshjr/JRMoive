import React from 'react';

interface CardProps {
  children: React.ReactNode;
  title?: string;
  subtitle?: string;
  className?: string;
  hoverable?: boolean;
}

export const Card: React.FC<CardProps> = ({
  children,
  title,
  subtitle,
  className = '',
  hoverable = false,
}) => {
  return (
    <div
      className={`card-apple ${hoverable ? '' : 'hover:shadow-apple-md hover:transform-none'} ${className}`}
    >
      {(title || subtitle) && (
        <div className="mb-4">
          {title && (
            <h3 className="text-apple-title-3 font-semibold text-text-primary">
              {title}
            </h3>
          )}
          {subtitle && (
            <p className="text-apple-subheadline text-text-secondary mt-1">
              {subtitle}
            </p>
          )}
        </div>
      )}
      {children}
    </div>
  );
};

export default Card;

