import React, { lazy } from 'react';
import { UserRole } from '../types';
import { LayoutDashboard, Package, CalendarClock, DollarSign, Flame, Users2, Bell, ShieldCheck } from 'lucide-react';

const DashboardPage     = lazy(() => import('../pages/DashboardPage'));
const ProductsPage      = lazy(() => import('../pages/ProductsPage'));
const BatchesPage       = lazy(() => import('../pages/BatchesPage'));
const CostsPage         = lazy(() => import('../pages/CostsPage'));
const ConsumptionPage   = lazy(() => import('../pages/ConsumptionPage'));
const HeadcountPage     = lazy(() => import('../pages/HeadcountPage'));
const NotificationsPage = lazy(() => import('../pages/NotificationsPage'));
const AdminPage         = lazy(() => import('../pages/AdminPage'));

export interface RouteConfig {
  path: string;
  label: string;
  icon: React.ComponentType<{ size?: number }>;
  element: React.LazyExoticComponent<() => JSX.Element>;
  allowedRoles: UserRole[];
  inNav: boolean;
}

// Role-based access per ТЗ:
// Admin: full access + delete reports
// Storekeeper: can add products, search in batches, cannot edit existing batches/products/expiry, renamed consumption section
// UPP (manager): consumption only date + total amount (no product breakdown), no access to products/batches
// UOP (nutrition_manager): view-only products/batches, no headcount editing, dashboard with urgent/expired items, cost per day table with average

export const appRoutes: RouteConfig[] = [
  { path: '/',             label: 'Дашборд',          icon: LayoutDashboard, element: DashboardPage,     allowedRoles: [],                                                    inNav: true },
  { path: '/products',     label: 'Продукты',         icon: Package,         element: ProductsPage,      allowedRoles: ['admin', 'manager', 'storekeeper', 'nutrition_manager'], inNav: true },
  { path: '/batches',      label: 'Партии / Сроки',   icon: CalendarClock,   element: BatchesPage,       allowedRoles: ['admin', 'manager', 'storekeeper', 'nutrition_manager'], inNav: true },
  { path: '/costs',        label: 'Себестоимость',    icon: DollarSign,      element: CostsPage,         allowedRoles: ['admin', 'manager', 'nutrition_manager'],                  inNav: true },
  { path: '/consumption',  label: 'Расход сырья',     icon: Flame,           element: ConsumptionPage,   allowedRoles: ['admin', 'manager', 'storekeeper', 'nutrition_manager'], inNav: true },
  { path: '/headcount',    label: 'Питающиеся',       icon: Users2,          element: HeadcountPage,     allowedRoles: ['admin', 'manager'],                                       inNav: true },
  { path: '/notifications',label: 'Уведомления',      icon: Bell,            element: NotificationsPage, allowedRoles: ['admin', 'manager'],                                       inNav: true },
  { path: '/admin',        label: 'Администрирование', icon: ShieldCheck,    element: AdminPage,         allowedRoles: ['admin'],                                            inNav: true },
];