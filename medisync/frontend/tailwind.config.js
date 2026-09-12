export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        primary: { 50:'#EFF6FF', 100:'#DBEAFE', 500:'#3B82F6', 600:'#2563EB', 700:'#1D4ED8' },
        surface: '#F9FAFB',
        ink: '#111827',
        muted: '#6B7280',
        border: '#E5E7EB',
        success: { bg:'#F0FDF4', text:'#16A34A', border:'#BBF7D0' },
        warning: { bg:'#FFFBEB', text:'#D97706', border:'#FDE68A' },
        danger:  { bg:'#FEF2F2', text:'#DC2626', border:'#FECACA' },
      },
      fontFamily: { sans: ['Inter', 'system-ui', 'sans-serif'] },
    },
  },
}
