import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { RootLayout } from '../layouts/RootLayout';
import { AccountLayout } from '../layouts/AccountLayout';
import { AdminLayout } from '../layouts/AdminLayout';
import { ProtectedRoute } from './ProtectedRoute';

// Customer & Public Pages
import { HomePage } from '../pages/HomePage';
import { ProductsPage } from '../pages/ProductsPage';
import { ProductDetailPage } from '../pages/ProductDetailPage';
import { CartPage } from '../pages/CartPage';
import { CheckoutPage } from '../pages/CheckoutPage';
import { OrderSuccessPage } from '../pages/OrderSuccessPage';
import { OrdersPage } from '../pages/OrdersPage';
import { OrderDetailPage } from '../pages/OrderDetailPage';
import { ProfilePage } from '../pages/ProfilePage';
import { AddressesPage } from '../pages/AddressesPage';
import { LoginPage } from '../pages/LoginPage';
import { RegisterPage } from '../pages/RegisterPage';
import { PaymentReturnPage } from '../pages/PaymentReturnPage';
import { NotFoundPage } from '../pages/NotFoundPage';

// Admin Pages
import { AdminDashboardPage } from '../pages/AdminDashboardPage';
import { AdminOrdersPage } from '../pages/AdminOrdersPage';
import { AdminOrderDetailPage } from '../pages/AdminOrderDetailPage';
import { AdminProductsPage } from '../pages/AdminProductsPage';
import { AdminProductFormPage } from '../pages/AdminProductFormPage';
import { AdminCategoriesPage } from '../pages/AdminCategoriesPage';
import { AdminUsersPage } from '../pages/AdminUsersPage';

export const AppRoutes: React.FC = () => {
  return (
    <Routes>
      {/* ----------------- CUSTOMER & PUBLIC AREA (RootLayout) ----------------- */}
      <Route element={<RootLayout />}>
        {/* Public Routes */}
        <Route path="/" element={<HomePage />} />
        <Route path="/products" element={<ProductsPage />} />
        <Route path="/products/:slug" element={<ProductDetailPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />

        {/* VNPAY Return Route (Public callback handler) */}
        <Route path="/payment/return" element={<PaymentReturnPage />} />
        <Route path="/payment-result" element={<PaymentReturnPage />} />

        {/* Customer Protected Routes */}
        <Route element={<ProtectedRoute requireCustomer={true} />}>
          <Route path="/cart" element={<CartPage />} />
          <Route path="/checkout" element={<CheckoutPage />} />
          <Route path="/order-success" element={<OrderSuccessPage />} />
          <Route path="/orders/:id" element={<OrderDetailPage />} />

          {/* Account Sub-routes with Sidebar Layout */}
          <Route element={<AccountLayout />}>
            <Route path="/orders" element={<OrdersPage />} />
            <Route path="/account" element={<Navigate to="/account/profile" replace />} />
            <Route path="/account/profile" element={<ProfilePage />} />
            <Route path="/account/addresses" element={<AddressesPage />} />
          </Route>
        </Route>

        {/* 404 Catch-All */}
        <Route path="*" element={<NotFoundPage />} />
      </Route>

      {/* ----------------- ADMIN AREA (AdminLayout) ----------------- */}
      <Route element={<ProtectedRoute requireAdmin={true} />}>
        <Route element={<AdminLayout />}>
          <Route path="/admin" element={<Navigate to="/admin/dashboard" replace />} />
          <Route path="/admin/dashboard" element={<AdminDashboardPage />} />
          <Route path="/admin/orders" element={<AdminOrdersPage />} />
          <Route path="/admin/orders/:id" element={<AdminOrderDetailPage />} />
          <Route path="/admin/products" element={<AdminProductsPage />} />
          <Route path="/admin/products/new" element={<AdminProductFormPage />} />
          <Route path="/admin/products/:id/edit" element={<AdminProductFormPage />} />
          <Route path="/admin/categories" element={<AdminCategoriesPage />} />
          <Route path="/admin/users" element={<AdminUsersPage />} />
        </Route>
      </Route>
    </Routes>
  );
};
