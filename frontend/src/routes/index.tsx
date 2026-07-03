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

export const appRoutes: RouteConfig[] = [
  { path: '/',             label: 'Дашборд',         icon: LayoutDashboard, element: DashboardPage,     allowedRoles: [],                                            inNav: true },
  { path: '/products',     label: 'Продукты',        icon: Package,         element: ProductsPage,      allowedRoles: [],                                            inNav: true },
  { path: '/batches',      label: 'Партии / Сроки',  icon: CalendarClock,   element: BatchesPage,       allowedRoles: [],                                            inNav: true },
  { path: '/costs',        label: 'Себестоимость',   icon: DollarSign,      element: CostsPage,         allowedRoles: ['admin','manager','nutrition_manager'],        inNav: true },
  { path: '/consumption',  label: 'Расход',          icon: Flame,           element: ConsumptionPage,   allowedRoles: ['admin','manager','nutrition_manager'],        inNav: true },
  { path: '/headcount',    label: 'Питающиеся',      icon: Users2,          element: HeadcountPage,     allowedRoles: ['admin','manager'],                           inNav: true },
  { path: '/notifications',label: 'Уведомления',     icon: Bell,            element: NotificationsPage, allowedRoles: ['admin','manager'],                           inNav: true },
  { path: '/admin',        label: 'Администрирование',icon: ShieldCheck,    element: AdminPage,         allowedRoles: ['admin'],                                     inNav: true },
];