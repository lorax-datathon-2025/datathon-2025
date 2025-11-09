import { NavLink } from "@/components/NavLink";
import { Shield, Home, LayoutDashboard, Upload } from "lucide-react";

const Navbar = () => {
  return (
    <nav className="border-b border-border bg-card/50 backdrop-blur-sm sticky top-0 z-50">
      <div className="container mx-auto px-4">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center gap-2">
            <div className="bg-gradient-hero p-2 rounded-lg">
              <Shield className="w-6 h-6 text-primary-foreground" />
            </div>
            <span className="text-xl font-bold bg-gradient-to-r from-primary to-info bg-clip-text text-transparent">
              DocGuard AI
            </span>
          </div>
          
          <div className="flex items-center gap-1">
            <NavLink
              to="/"
              className="flex items-center gap-2 px-4 py-2 rounded-lg transition-all hover:bg-accent"
              activeClassName="bg-accent text-accent-foreground font-medium"
            >
              <Home className="w-4 h-4" />
              <span>Home</span>
            </NavLink>
            <NavLink
              to="/dashboard"
              className="flex items-center gap-2 px-4 py-2 rounded-lg transition-all hover:bg-accent"
              activeClassName="bg-accent text-accent-foreground font-medium"
            >
              <LayoutDashboard className="w-4 h-4" />
              <span>Dashboard</span>
            </NavLink>
            <NavLink
              to="/upload"
              className="flex items-center gap-2 px-4 py-2 rounded-lg transition-all hover:bg-accent"
              activeClassName="bg-accent text-accent-foreground font-medium"
            >
              <Upload className="w-4 h-4" />
              <span>Upload</span>
            </NavLink>
          </div>
        </div>
      </div>
    </nav>
  );
};

export default Navbar;