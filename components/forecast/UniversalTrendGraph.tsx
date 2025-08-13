import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Area, Legend } from 'recharts';
import { motion } from 'framer-motion';

interface DataPoint {
  x: string;
  y: number;
  upper?: number;
  lower?: number;
}

interface UniversalTrendGraphProps {
  historic: DataPoint[];
  forecast: DataPoint[];
  xLabel?: string;
  yLabel?: string;
  lineLabel?: string;
  color?: string;
  height?: number;
  fadeIn?: boolean;
  theme?: 'light' | 'dark';
  showDots?: boolean;
  confidence?: string;
  volatility?: string;
  data_points?: number;
}

const UniversalTrendGraph: React.FC<UniversalTrendGraphProps> = ({
  historic,
  forecast,
  xLabel = 'Date',
  yLabel = 'Value',
  lineLabel = 'Value',
  color = '#1C2D45',
  height = 380,
  fadeIn = true,
  theme = 'light',
  showDots = false,
}) => {
  // Transform data into a single continuous array with forecast flag
  const transformData = () => {
    if (historic.length === 0 || forecast.length === 0) {
      return [...historic, ...forecast].map(point => ({
        date: point.x,
        price: point.y,
        forecast: false,
        upper: point.upper,
        lower: point.lower
      }));
    }

    // Create a truly continuous dataset
    const allData = [...historic];
    
    // Add all forecast points directly (no bridge point needed)
    allData.push(...forecast);
    
    return allData.map((point, index) => {
      const isForecast = index >= historic.length;
      
      return {
        date: point.x,
        price: point.y,
        forecast: isForecast,
        upper: point.upper,
        lower: point.lower
      };
    });
  };

  const chartData = transformData();
  const hasBands = forecast.some((d) => d.upper !== undefined && d.lower !== undefined);

  // Calculate proper Y-axis domain
  const calculateYDomain = () => {
    const allValues = [...historic.map(d => d.y), ...forecast.map(d => d.y)];
    const minValue = Math.min(...allValues);
    const maxValue = Math.max(...allValues);
    const range = maxValue - minValue;
    
    // Start at minimum value, add 10-15% headroom at top
    const minDomain = Math.max(0, minValue - range * 0.05);
    const maxDomain = maxValue + range * 0.15;
    
    return [minDomain, maxDomain];
  };

  const yDomain = calculateYDomain();

  // Custom tooltip formatter
  const formatTooltip = (value: any, name: string) => {
    if (typeof value === 'number') {
      return [`£${value.toFixed(2)}`, 'Price'];
    }
    return [value, name];
  };

  // Custom label formatter for dates - short month + year format
  const formatDate = (tickItem: string) => {
    try {
      const date = new Date(tickItem);
      return date.toLocaleDateString('en-GB', { 
        month: 'short', 
        year: 'numeric' 
      });
    } catch {
      return tickItem;
    }
  };

  // Custom Y-axis tick formatter
  const formatYAxis = (value: number) => {
    return `£${value.toFixed(2)}`;
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 24 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.7, ease: 'easeOut' }}
      style={{ background: 'transparent' }}
    >
      <ResponsiveContainer width="100%" height={height}>
        <LineChart 
          data={chartData} 
          margin={{ top: 24, right: 32, left: 8, bottom: 24 }}
        >
          {/* Subtle grid lines */}
          <CartesianGrid 
            strokeDasharray="3 3" 
            stroke={theme === 'dark' ? '#374151' : '#f3f4f6'} 
            strokeOpacity={0.5}
          />
          
          {/* X-axis with proper date formatting */}
          <XAxis 
            dataKey="date" 
            tick={{ 
              fill: theme === 'dark' ? '#e5e7eb' : '#374151',
              fontSize: 12
            }} 
            label={{ 
              value: xLabel, 
              position: 'insideBottom', 
              offset: -8, 
              fill: theme === 'dark' ? '#e5e7eb' : '#374151' 
            }}
            tickFormatter={formatDate}
            interval="preserveStartEnd"
            minTickGap={30}
          />
          
          {/* Y-axis with proper domain and formatting */}
          <YAxis 
            tick={{ 
              fill: theme === 'dark' ? '#e5e7eb' : '#374151',
              fontSize: 12
            }} 
            label={{ 
              value: yLabel, 
              angle: -90, 
              position: 'insideLeft', 
              fill: theme === 'dark' ? '#e5e7eb' : '#374151' 
            }}
            tickFormatter={formatYAxis}
            domain={yDomain}
          />
          
          {/* Enhanced tooltip */}
          <Tooltip
            contentStyle={{ 
              background: theme === 'dark' ? '#1f2937' : '#fff', 
              border: '1px solid #d1d5db', 
              borderRadius: 8,
              boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)'
            }}
            labelStyle={{ color: theme === 'dark' ? '#fff' : '#222' }}
            formatter={formatTooltip}
            labelFormatter={(label) => {
              try {
                const date = new Date(label);
                return date.toLocaleDateString('en-GB', { 
                  weekday: 'long', 
                  year: 'numeric', 
                  month: 'long', 
                  day: 'numeric' 
                });
              } catch {
                return label;
              }
            }}
            isAnimationActive={true}
            animationDuration={300}
          />
          
          {/* Confidence bands with subtle shading */}
          {hasBands && (
            <Area
              type="monotone"
              dataKey="upper"
              stroke="transparent"
              fill={color}
              fillOpacity={0.08}
              isAnimationActive={fadeIn}
              dot={false}
              activeDot={false}
              legendType="none"
            />
          )}
          {hasBands && (
            <Area
              type="monotone"
              dataKey="lower"
              stroke="transparent"
              fill={color}
              fillOpacity={0.08}
              isAnimationActive={fadeIn}
              dot={false}
              activeDot={false}
              legendType="none"
            />
          )}
          
          {/* Historical data line (solid) */}
          <Line
            type="monotone"
            dataKey="price"
            stroke="#1e293b"
            strokeWidth={2}
            dot={false}
            name="Historical Price"
            isAnimationActive={fadeIn}
            animationDuration={800}
            activeDot={{ 
              r: 4, 
              stroke: '#1e293b', 
              strokeWidth: 2, 
              fill: '#fff' 
            }}
            // Only show historical data
            data={chartData.filter(d => !d.forecast)}
          />
          
          {/* Forecast data line (dashed) */}
          {forecast.length > 0 && (
            <Line
              type="monotone"
              dataKey="price"
              stroke="#94a3b8"
              strokeWidth={2}
              strokeDasharray="5 5"
              dot={false}
              name="Forecast"
              isAnimationActive={fadeIn}
              animationDuration={800}
              animationBegin={800}
              activeDot={{ 
                r: 4, 
                stroke: '#94a3b8', 
                strokeWidth: 2, 
                fill: '#fff' 
              }}
              // Only show forecast data
              data={chartData.filter(d => d.forecast)}
            />
          )}
        </LineChart>
      </ResponsiveContainer>
    </motion.div>
  );
};

export default UniversalTrendGraph; 