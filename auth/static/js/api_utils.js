/**
 * API Utilities for Authentication and Requests
 */

// Store tokens in localStorage
const TOKEN_KEY = 'auth_token';
const REFRESH_TOKEN_KEY = 'refresh_token';

/**
 * Save authentication tokens to localStorage
 * @param {string} token - JWT access token
 * @param {string} refreshToken - JWT refresh token
 */
function saveTokens(token, refreshToken) {
    localStorage.setItem(TOKEN_KEY, token);
    localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
}

/**
 * Get the current JWT token
 * @returns {string|null} The JWT token or null if not found
 */
function getToken() {
    return localStorage.getItem(TOKEN_KEY);
}

/**
 * Get the refresh token
 * @returns {string|null} The refresh token or null if not found
 */
function getRefreshToken() {
    return localStorage.getItem(REFRESH_TOKEN_KEY);
}

/**
 * Clear authentication tokens
 */
function clearTokens() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
}

/**
 * Check if user is authenticated
 * @returns {boolean} True if authenticated
 */
function isAuthenticated() {
    return !!getToken();
}

/**
 * Make an authenticated API request
 * @param {string} url - API endpoint URL
 * @param {Object} options - Fetch options
 * @returns {Promise} Fetch promise
 */
async function apiRequest(url, options = {}) {
    // Get the CSRF token from the cookie
    const csrfToken = getCookie('csrftoken');
    
    // Default headers with authentication
    const headers = {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken,
        ...options.headers
    };

    // Add Authorization header if we have a token
    const token = getToken();
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }

    // Merge options
    const requestOptions = {
        ...options,
        headers,
        credentials: 'include', // Include cookies
    };

    try {
        const response = await fetch(url, requestOptions);
        
        // If unauthorized and we have a refresh token, try to refresh
        if (response.status === 401 && getRefreshToken()) {
            const refreshed = await refreshAuthToken();
            if (refreshed) {
                // Retry the request with the new token
                headers['Authorization'] = `Bearer ${getToken()}`;
                return fetch(url, {
                    ...requestOptions,
                    headers
                });
            }
        }
        
        return response;
    } catch (error) {
        console.error('API Request Error:', error);
        throw error;
    }
}

/**
 * Refresh the authentication token
 * @returns {Promise<boolean>} True if refresh was successful
 */
async function refreshAuthToken() {
    const refreshToken = getRefreshToken();
    if (!refreshToken) return false;

    try {
        const response = await fetch('/auth/token/refresh/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ refresh: refreshToken }),
        });

        if (response.ok) {
            const data = await response.json();
            localStorage.setItem(TOKEN_KEY, data.access);
            return true;
        } else {
            // If refresh fails, clear tokens and require re-login
            clearTokens();
            return false;
        }
    } catch (error) {
        console.error('Token refresh error:', error);
        clearTokens();
        return false;
    }
}

/**
 * Get a cookie value by name
 * @param {string} name - Cookie name
 * @returns {string} Cookie value
 */
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Export functions for use in other scripts
window.apiUtils = {
    saveTokens,
    getToken,
    getRefreshToken,
    clearTokens,
    isAuthenticated,
    apiRequest,
    refreshAuthToken,
    getCookie
};
