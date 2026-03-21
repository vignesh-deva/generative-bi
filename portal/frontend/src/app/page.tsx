"use client";

import { useEffect, useState } from "react";
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { IndianRupee, ShoppingCart, TrendingUp } from "lucide-react";
import { fetchDashboard } from "@/lib/api";
import KpiCard from "@/components/KpiCard";
import ChartCard from "@/components/ChartCard";

const CHART_COLORS = [
  "#3b82f6",
  "#10b981",
  "#f59e0b",
  "#ef4444",
  "#8b5cf6",
  "#ec4899",
];

const CHART_GRID = { stroke: "#f1f5f9", strokeDasharray: "none" };
const AXIS_STYLE = { fontSize: 11, fill: "#94a3b8" };
const TOOLTIP_STYLE = {
  contentStyle: {
    borderRadius: "8px",
    border: "1px solid #e2e8f0",
    boxShadow: "0 4px 6px -1px rgba(0,0,0,0.06)",
    fontSize: "12px",
    padding: "8px 12px",
  },
};

function formatINR(n: number): string {
  if (n >= 1_00_00_000) return `${(n / 1_00_00_000).toFixed(2)} Cr`;
  if (n >= 1_00_000) return `${(n / 1_00_000).toFixed(2)} L`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)} K`;
  return n.toLocaleString("en-IN");
}

type CategoryRevenue = { category: string; revenue: number };
type MonthlyTrend = { month: string; revenue: number };
type ProductRevenue = { product: string; revenue: number };
type ZoneRevenue = { zone: string; revenue: number };
type OrderStatus = { status: string; count: number };
type CategoryStock = { category: string; stock: number };

export default function DashboardPage() {
  const [totalRevenue, setTotalRevenue] = useState<number | null>(null);
  const [totalOrders, setTotalOrders] = useState<number | null>(null);
  const [avgOrderValue, setAvgOrderValue] = useState<number | null>(null);
  const [revenueByCategory, setRevenueByCategory] = useState<CategoryRevenue[]>([]);
  const [monthlyTrend, setMonthlyTrend] = useState<MonthlyTrend[]>([]);
  const [topProducts, setTopProducts] = useState<ProductRevenue[]>([]);
  const [salesByZone, setSalesByZone] = useState<ZoneRevenue[]>([]);
  const [orderFulfillment, setOrderFulfillment] = useState<OrderStatus[]>([]);
  const [inventoryByCategory, setInventoryByCategory] = useState<CategoryStock[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const [rev, ord, avg, cat, trend, top, zone, fulfill, inv] =
          await Promise.all([
            fetchDashboard<{ total_revenue: number }>("total-revenue"),
            fetchDashboard<{ total_orders: number }>("total-orders"),
            fetchDashboard<{ avg_order_value: number }>("avg-order-value"),
            fetchDashboard<CategoryRevenue[]>("revenue-by-category"),
            fetchDashboard<MonthlyTrend[]>("monthly-sales-trend"),
            fetchDashboard<ProductRevenue[]>("top-products"),
            fetchDashboard<ZoneRevenue[]>("sales-by-zone"),
            fetchDashboard<OrderStatus[]>("order-fulfillment"),
            fetchDashboard<CategoryStock[]>("inventory-by-category"),
          ]);
        setTotalRevenue(rev.total_revenue);
        setTotalOrders(ord.total_orders);
        setAvgOrderValue(avg.avg_order_value);
        setRevenueByCategory(cat);
        setMonthlyTrend(trend);
        setTopProducts(top);
        setSalesByZone(zone);
        setOrderFulfillment(fulfill);
        setInventoryByCategory(inv);
      } catch (e) {
        console.error("Failed to load dashboard data:", e);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-blue-500 border-t-transparent" />
          <p className="text-sm text-[var(--text-muted)]">
            Loading dashboard...
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-xl font-bold text-[var(--text-primary)]">
          Dashboard
        </h1>
        <p className="mt-0.5 text-sm text-[var(--text-muted)]">
          FMCG supply chain performance overview
        </p>
      </div>

      <div className="grid grid-cols-3 gap-5">
        {/* Row 1: KPI Cards */}
        <KpiCard
          title="Total Revenue"
          value={totalRevenue !== null ? `₹${formatINR(totalRevenue)}` : "--"}
          icon={<IndianRupee size={22} />}
          accent="#3b82f6"
        />
        <KpiCard
          title="Total Orders"
          value={totalOrders !== null ? totalOrders.toLocaleString("en-IN") : "--"}
          icon={<ShoppingCart size={22} />}
          accent="#10b981"
        />
        <KpiCard
          title="Avg Order Value"
          value={avgOrderValue !== null ? `₹${formatINR(avgOrderValue)}` : "--"}
          icon={<TrendingUp size={22} />}
          accent="#8b5cf6"
        />

        {/* Row 2: Charts */}
        <ChartCard title="Revenue by Category">
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={revenueByCategory} barCategoryGap="25%">
              <CartesianGrid vertical={false} {...CHART_GRID} />
              <XAxis
                dataKey="category"
                tick={AXIS_STYLE}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                tickFormatter={(v) => formatINR(v)}
                tick={AXIS_STYLE}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip
                formatter={(v) => `₹${formatINR(Number(v))}`}
                {...TOOLTIP_STYLE}
              />
              <Bar dataKey="revenue" fill="#3b82f6" radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Monthly Sales Trend">
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={monthlyTrend}>
              <CartesianGrid vertical={false} {...CHART_GRID} />
              <XAxis
                dataKey="month"
                tick={AXIS_STYLE}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                tickFormatter={(v) => formatINR(v)}
                tick={AXIS_STYLE}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip
                formatter={(v) => `₹${formatINR(Number(v))}`}
                {...TOOLTIP_STYLE}
              />
              <Line
                type="monotone"
                dataKey="revenue"
                stroke="#10b981"
                strokeWidth={2.5}
                dot={{ r: 4, fill: "#10b981", strokeWidth: 2, stroke: "#fff" }}
                activeDot={{ r: 6, fill: "#10b981", strokeWidth: 2, stroke: "#fff" }}
              />
            </LineChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Top 10 Products by Revenue">
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={topProducts} layout="vertical" barCategoryGap="20%">
              <CartesianGrid horizontal={false} {...CHART_GRID} />
              <XAxis
                type="number"
                tickFormatter={(v) => formatINR(v)}
                tick={AXIS_STYLE}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                type="category"
                dataKey="product"
                width={130}
                tick={{ fontSize: 10, fill: "#64748b" }}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip
                formatter={(v) => `₹${formatINR(Number(v))}`}
                {...TOOLTIP_STYLE}
              />
              <Bar dataKey="revenue" fill="#f59e0b" radius={[0, 6, 6, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        {/* Row 3: Charts */}
        <ChartCard title="Sales by Zone">
          <ResponsiveContainer width="100%" height={260}>
            <PieChart>
              <Pie
                data={salesByZone}
                dataKey="revenue"
                nameKey="zone"
                cx="50%"
                cy="50%"
                innerRadius={55}
                outerRadius={95}
                paddingAngle={3}
                label={({ name, percent }) =>
                  `${name} ${((percent ?? 0) * 100).toFixed(0)}%`
                }
              >
                {salesByZone.map((_, i) => (
                  <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                ))}
              </Pie>
              <Tooltip
                formatter={(v) => `₹${formatINR(Number(v))}`}
                {...TOOLTIP_STYLE}
              />
            </PieChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Order Fulfillment Status">
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={orderFulfillment} barCategoryGap="25%">
              <CartesianGrid vertical={false} {...CHART_GRID} />
              <XAxis
                dataKey="status"
                tick={AXIS_STYLE}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                tick={AXIS_STYLE}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip {...TOOLTIP_STYLE} />
              <Bar dataKey="count" radius={[6, 6, 0, 0]}>
                {orderFulfillment.map((entry, i) => {
                  const colorMap: Record<string, string> = {
                    Fulfilled: "#10b981",
                    Partial: "#f59e0b",
                    Pending: "#3b82f6",
                    Cancelled: "#ef4444",
                  };
                  return (
                    <Cell
                      key={i}
                      fill={colorMap[entry.status] || CHART_COLORS[i]}
                    />
                  );
                })}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Inventory Levels by Category">
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={inventoryByCategory} barCategoryGap="25%">
              <CartesianGrid vertical={false} {...CHART_GRID} />
              <XAxis
                dataKey="category"
                tick={AXIS_STYLE}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                tick={AXIS_STYLE}
                axisLine={false}
                tickLine={false}
                tickFormatter={(v) => v.toLocaleString()}
              />
              <Tooltip {...TOOLTIP_STYLE} />
              <Bar dataKey="stock" fill="#8b5cf6" radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>
    </div>
  );
}
