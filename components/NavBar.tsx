import React, { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/router';
import { Menu, X, ChevronDown } from 'lucide-react';

const NavBar: React.FC = () => {
  const router = useRouter();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  const navItems = [
    { href: '/', label: 'Dashboard', icon: '🏠' },
    { href: '/analytics/', label: 'Analytics', icon: '📊' },
    { href: '/invoices/', label: 'Invoices', icon: '📄' },
    { href: '/document-queue/', label: 'Document Queue', icon: '📋' },
    { href: '/flagged/', label: 'Flagged Issues', icon: '⚠️' },
    { href: '/suppliers/', label: 'Suppliers', icon: '🏢' },
    { href: '/product-trends/', label: 'Product Trends', icon: '📈' },
    { href: '/notes/', label: 'Notes', icon: '📝' },
    { href: '/settings/', label: 'Settings', icon: '⚙️' },
  ];

  const isActive = (href: string) => {
    if (href === '/') {
      return router.pathname === '/';
    }
    // Handle trailing slashes for Next.js compatibility
    const pathname = router.pathname.endsWith('/') ? router.pathname : router.pathname + '/';
    const hrefWithSlash = href.endsWith('/') ? href : href + '/';
    return pathname.startsWith(hrefWithSlash);
  };

  const handleNavClick = (href: string, label: string) => {
    console.log(`Navigation clicked: ${label} -> ${href}`);
    // Close mobile menu when navigation item is clicked
    setIsMobileMenuOpen(false);
  };

  const toggleMobileMenu = () => {
    setIsMobileMenuOpen(!isMobileMenuOpen);
  };

  return (
    <nav className="bg-white shadow-md border-b border-gray-200 relative z-[9999] pointer-events-auto" style={{ zIndex: 9999 }}>
      <div className="container mx-auto px-4">
        <div className="flex justify-between items-center h-16">
          {/* Logo */}
          <div className="flex items-center">
            <Link 
              href="/" 
              className="flex items-center space-x-2 hover:opacity-80 transition-opacity"
              onClick={() => handleNavClick('/', 'Logo')}
            >
              <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
                <span className="text-white font-bold text-lg">O</span>
              </div>
              <span className="text-xl font-bold text-gray-900">Owlin</span>
            </Link>
          </div>

          {/* Desktop Navigation Links */}
          <div className="hidden lg:flex items-center space-x-1 flex-1 justify-center">
            {navItems.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => handleNavClick(item.href, item.label)}
                className={`
                  px-4 py-2 rounded-lg text-sm font-medium transition-colors duration-200
                  cursor-pointer select-none relative z-[10000]
                  ${isActive(item.href)
                    ? 'bg-blue-100 text-blue-700'
                    : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
                  }
                `}
                style={{ zIndex: 10000 }}
              >
                <span className="mr-2">{item.icon}</span>
                {item.label}
              </Link>
            ))}
          </div>

          {/* Mobile Menu Button */}
          <div className="lg:hidden">
            <button 
              className="p-2 rounded-lg text-gray-600 hover:text-gray-900 hover:bg-gray-100 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500"
              onClick={toggleMobileMenu}
              aria-label="Toggle mobile menu"
              aria-expanded={isMobileMenuOpen}
            >
              {isMobileMenuOpen ? (
                <X className="w-6 h-6" />
              ) : (
                <Menu className="w-6 h-6" />
              )}
            </button>
          </div>
        </div>

        {/* Enhanced Mobile Navigation */}
        <div className={`
          lg:hidden border-t border-gray-200 transition-all duration-300 ease-in-out overflow-hidden
          ${isMobileMenuOpen ? 'max-h-96 opacity-100' : 'max-h-0 opacity-0'}
        `}>
          <div className="py-4 space-y-2">
            {navItems.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => handleNavClick(item.href, item.label)}
                className={`
                  block px-4 py-3 rounded-lg text-sm font-medium transition-colors duration-200
                  cursor-pointer select-none relative z-[10000] mx-2
                  ${isActive(item.href)
                    ? 'bg-blue-100 text-blue-700'
                    : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
                  }
                `}
                style={{ zIndex: 10000 }}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center">
                    <span className="mr-3 text-lg">{item.icon}</span>
                    <span>{item.label}</span>
                  </div>
                  {isActive(item.href) && (
                    <div className="w-2 h-2 bg-blue-600 rounded-full"></div>
                  )}
                </div>
              </Link>
            ))}
          </div>
        </div>
      </div>
    </nav>
  );
};

export default NavBar; 