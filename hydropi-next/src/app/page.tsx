/* eslint-disable @typescript-eslint/no-explicit-any */

"use client";

import { useEffect, useState } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  LabelList,
  Cell,
} from "recharts";

export default function Home() {
  const [data, setData] = useState<any[]>([]);
  const [uptime, setUptime] = useState<string>("Loading...");
  const [services, setServices] = useState<any[]>([]);
  const [isClient, setIsClient] = useState(false);

  useEffect(() => {
    setIsClient(true);

    // Fetch data from the status API
    const fetchData = async () => {
      try {
        const response = await fetch("https://api-norway.hydropi.io/status");
        const result = await response.json();

        // Extract memory data and calculate usage percentage
        const memory = result.memory;
        const memoryPercent = ((memory.used / memory.total) * 100).toFixed(1);

        // Map API response to chart data
        const chartData: any = [
          {
            name: "Temperature",
            value: result.temperature,
            unit: "°C",
            max: 75, // Example threshold for temperature
          },
          {
            name: "CPU Usage",
            value: result.cpu_usage,
            unit: "%",
            max: 80, // Example threshold for CPU usage
          },
          {
            name: "Memory Usage",
            value: parseFloat(memoryPercent),
            unit: "%",
            max: 85, // Example threshold for memory usage
          },
        ];
        setData(chartData);

        // Set uptime
        setUptime(result.uptime);

        // Set services
        setServices(result.services || []);
      } catch (error) {
        console.error("Error fetching status data:", error);
        setUptime("Error fetching uptime");
      }
    };

    fetchData();
  }, []);

  const getBarColor = (value: number, max: number) => {
    if (value > max) {
      return "#ff4d4d"; // Red for exceeding the threshold
    } else if (value <= max * 0.8) {
      return "#4caf50"; // Green for safe values
    }
    return "#8884d8"; // Default purple for moderate values
  };

  const CustomLabel = (props: {
    x?: number;
    y?: number;
    width?: number;
    height?: number;
    value?: number;
    index?: number;
  }) => {
    const { x, y, width, height, value, index } = props;
    const unit = data[index!]?.unit || ""; // Safely get the unit
    const max = data[index!]?.max || 100; // Safely get the max threshold
    const isOverMax = value && value > max;

    return (
      <text
        x={(x || 0) + (width || 0) / 2} // Position text at the center of the bar
        y={(y || 0) + (height || 0) / 2 + 5} // Center vertically with slight adjustment
        fill="#ffffff"
        fontSize="16" // Increased font size for the value text
        fontWeight="bold"
        textAnchor="middle" // Center text horizontally
      >
        {`${value}${unit}`} {isOverMax && "🔥"}
      </text>
    );
  };

  const CustomTooltip = ({
    active,
    payload,
  }: {
    active?: boolean;
    payload?: any[];
  }) => {
    if (active && payload && payload.length) {
      const { name, value, unit, max } = payload[0].payload;
      return (
        <div
          style={{
            backgroundColor: "#333",
            color: "#fff",
            padding: "10px",
            borderRadius: "5px",
          }}
        >
          <p>
            <strong>{name}</strong>
          </p>
          <p>
            Value: {value}
            {unit} {value > max ? "🔥" : ""}
          </p>
          <p>Expected Max: {max}{unit}</p>
        </div>
      );
    }
    return null;
  };

  if (!isClient || data.length === 0) {
    // Prevent rendering on the server or before data is fetched
    return <p>Loading...</p>;
  }

  return (
    <div style={{ textAlign: "center", width: "80%", margin: "0 auto" }}>
      <h1>HydroPi Status</h1>
      <p style={{ marginBottom: "20px", fontSize: "18px", fontWeight: "bold" }}>
        Uptime: {uptime}
      </p>
      <div style={{ width: "100%", height: 400 }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            layout="vertical"
            data={data}
            margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
          >
            <XAxis type="number" domain={[0, 100]} hide />
            <YAxis
              type="category"
              dataKey="name"
              tick={{ fontSize: 12 }}
              width={100}
            />
            <Tooltip content={<CustomTooltip />} />
            <Bar dataKey="value" barSize={40}> {/* Increased bar width */}
              <LabelList content={<CustomLabel />} />
              {data.map((entry: any, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={getBarColor(entry.value, entry.max)}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <div style={{ marginTop: "20px" }}>
        <h2>Service Status</h2>
        <ul style={{ listStyleType: "none", padding: 0 }}>
          {services.map((service) => (
            <li
              key={service.name}
              style={{
                margin: "5px 0",
                color: service.status === "active" ? "#4caf50" : "#ff4d4d",
              }}
            >
              {service.name}: {service.status}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
