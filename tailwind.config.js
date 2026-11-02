/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./templates/**/*.html', './portal/**/*.py'],
  theme: {
    extend: {
      colors: {
        cream: '#f6f2e8',
        cream2: '#efeade',
        ink: '#17211b',
        ink2: '#3d4740',
        mute: '#6c7269',
        card: '#fffdf7',
        line: '#ddd4c1',
        line2: '#e9e2d2',
        pine: '#263b2c',
        pine2: '#1c2d21',
        pinesoft: '#e6ece7',
        gold: '#b29153',
        gold2: '#96773f',
        goldsoft: '#f4ecdc',
        water: '#2f6d6b',
        ok: '#2f6d4f',
        oksoft: '#e8f2ec',
        warn: '#8a6d1f',
        warnsoft: '#f7f0dc',
        danger: '#9b3b2c',
        dangersoft: '#fbeae6',
        info: '#2f5b6d',
        infosoft: '#e6eff3',
      },
      fontFamily: {
        sans: ['Vazirmatn', 'Tahoma', 'system-ui', 'sans-serif'],
      },
      boxShadow: {
        card: '0 1px 2px rgba(23,33,27,.05)',
        lift: '0 4px 14px rgba(23,33,27,.07)',
        deep: '0 14px 40px rgba(23,33,27,.10)',
      },
      maxWidth: {
        site: '1200px',
      },
      borderRadius: {
        xl2: '22px',
      },
    },
  },
  plugins: [],
};
