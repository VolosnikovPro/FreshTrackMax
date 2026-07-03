import { T } from '../components/common/UI';

export default () =>
  <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', background: T.bg, fontFamily: "'Onest', system-ui, sans-serif", padding: 24 }}>
    <div style={{ width: 60, height: 60, border: "6px solid #444", borderTopColor: "#09f", borderRadius: "50%", animation: "spin 1s linear infinite" }}/>
  </div>