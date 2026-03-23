/**
 * Zippy — the Zip2Job mascot.
 *
 * A cute zipped-folder character wearing a tie, rendered as inline SVG.
 * Supports two sizes ("sm" for sidebar icon, "lg" for the tour) and
 * expression variants: happy, wave, pointing, excited, thumbsup.
 */

const SIZES = { sm: 24, lg: 80 }

export default function Zippy({ size = 'lg', expression = 'happy', className = '' }) {
  const px = SIZES[size] ?? SIZES.lg
  const isLarge = size === 'lg'

  // Root animation class depends on expression
  const rootAnim = isLarge
    ? expression === 'excited'
      ? 'animate-zippy-excited'
      : 'animate-zippy-hop'
    : ''

  return (
    <svg
      viewBox="0 0 120 140"
      width={px}
      height={px * (140 / 120)}
      className={`inline-block ${isLarge ? 'animate-zippy-bounce' : ''} ${rootAnim} ${className}`}
      style={{ overflow: 'visible' }}
      aria-label="Zippy the folder mascot"
      role="img"
    >
      {/* Legs */}
      {isLarge && (
        <>
          <rect x="35" y="118" width="14" height="16" rx="5" fill="#c4841a" />
          <rect x="71" y="118" width="14" height="16" rx="5" fill="#c4841a" />
        </>
      )}

      {/* Body — rounded folder */}
      <rect x="15" y="30" width="90" height="90" rx="16" fill="#f5a623" />

      {/* Top fold / tab — wider and more prominent */}
      <path
        d="M15 44 Q15 28 31 28 L50 28 L58 18 Q61 14 66 14 L92 14 Q108 14 108 30 L108 44 Z"
        fill="#c4841a"
      />
      {/* Folder crease line below tab */}
      <line x1="20" y1="44" x2="100" y2="44" stroke="#b0740f" strokeWidth="1" strokeOpacity="0.5" />

      {/* Eyes — moved up to cy=48, well above zipper */}
      {expression === 'thumbsup' ? (
        <>
          {/* Left eye normal */}
          <ellipse cx="42" cy="48" rx="9" ry="10" fill="white" />
          <ellipse cx="44" cy="47" rx="5" ry="6" fill="#111318" />
          <circle cx="46" cy="45" r="2" fill="white" />
          {/* Right eye — wink */}
          <path
            d="M70 48 Q78 42 86 48"
            fill="none"
            stroke="#111318"
            strokeWidth="2.5"
            strokeLinecap="round"
          />
        </>
      ) : (
        <>
          {/* Left eye */}
          <ellipse cx="42" cy="48" rx="9" ry="10" fill="white" />
          <ellipse cx="44" cy="47" rx="5" ry="6" fill="#111318" />
          <circle cx="46" cy="45" r="2" fill="white" />
          {/* Right eye */}
          <ellipse cx="78" cy="48" rx="9" ry="10" fill="white" />
          <ellipse cx="80" cy="47" rx="5" ry="6" fill="#111318" />
          <circle cx="82" cy="45" r="2" fill="white" />
        </>
      )}

      {/* Eye blink overlay — periodic blink for large size */}
      {isLarge && expression !== 'thumbsup' && (
        <g>
          <rect className="animate-zippy-blink-rect" x="30" y="38" width="26" height="20" rx="9" fill="#f5a623" opacity="0" />
          <rect className="animate-zippy-blink-rect" x="66" y="38" width="26" height="20" rx="9" fill="#f5a623" opacity="0" />
          <style>{`
            .animate-zippy-blink-rect {
              animation: zippyBlinkRect 3.5s ease-in-out infinite;
            }
            @keyframes zippyBlinkRect {
              0%, 92%, 100% { opacity: 0; }
              95% { opacity: 1; }
            }
          `}</style>
        </g>
      )}

      {/* Mouth — moved up to y=58-66, clearly above zipper */}
      {expression === 'wave' ? (
        /* Open "O" mouth */
        <ellipse cx="60" cy="62" rx="6" ry="5" fill="#111318" />
      ) : expression === 'excited' ? (
        /* Wide grin */
        <path
          d="M44 58 Q52 72 60 72 Q68 72 76 58"
          fill="#111318"
          stroke="#111318"
          strokeWidth="1"
        />
      ) : (
        /* Default smile */
        <path
          d="M50 60 Q60 70 70 60"
          fill="none"
          stroke="#111318"
          strokeWidth="2.5"
          strokeLinecap="round"
        />
      )}

      {/* ── Zipper — the defining feature ── */}
      {/* Zipper teeth (small rects along the zigzag) */}
      {[25, 35, 45, 55, 65, 75, 85, 95].map((x) => (
        <g key={x}>
          <rect x={x - 1.5} y="73" width="3" height="4" rx="0.5" fill="#2c3140" />
          <rect x={x - 1.5} y="79" width="3" height="4" rx="0.5" fill="#2c3140" />
        </g>
      ))}
      {/* Zigzag line */}
      <polyline
        points="20,80 30,74 40,80 50,74 60,80 70,74 80,80 90,74 100,80"
        fill="none"
        stroke="#111318"
        strokeWidth="3"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      {/* Zipper pull — rectangular tab + circle */}
      <rect x="96" y="77" width="10" height="6" rx="2" fill="#111318" />
      <circle cx="101" cy="80" r="2" fill="#2c3140" />
      <rect x="104" y="78" width="4" height="4" rx="1" fill="#2c3140" />

      {/* Tie — larger and more visible */}
      <polygon points="60,88 53,101 60,112 67,101" fill="#c8cfe0" stroke="#9aa3b8" strokeWidth="1" />
      <polygon points="55,87 65,87 63,92 57,92" fill="#9aa3b8" stroke="#8590a6" strokeWidth="0.5" />

      {/* Arms — expression-dependent */}
      {isLarge && (
        <>
          {expression === 'wave' && (
            <>
              {/* Left arm waves */}
              <path
                d="M15 62 Q2 57 5 47"
                fill="none"
                stroke="#c4841a"
                strokeWidth="8"
                strokeLinecap="round"
                className="animate-zippy-wave"
                style={{ transformOrigin: '15px 62px' }}
              />
              {/* Right arm resting */}
              <path
                d="M105 62 Q118 57 115 47"
                fill="none"
                stroke="#c4841a"
                strokeWidth="8"
                strokeLinecap="round"
              />
            </>
          )}

          {expression === 'pointing' && (
            <>
              {/* Left arm resting */}
              <path
                d="M15 62 Q2 57 5 47"
                fill="none"
                stroke="#c4841a"
                strokeWidth="8"
                strokeLinecap="round"
              />
              {/* Right arm pointing upward */}
              <path
                d="M105 62 Q115 47 108 35"
                fill="none"
                stroke="#c4841a"
                strokeWidth="8"
                strokeLinecap="round"
                className="animate-zippy-point"
                style={{ transformOrigin: '105px 62px' }}
              />
              {/* Pointing finger */}
              <circle
                cx="108"
                cy="33"
                r="3"
                fill="#c4841a"
                className="animate-zippy-point"
                style={{ transformOrigin: '105px 62px' }}
              />
            </>
          )}

          {expression === 'excited' && (
            <>
              {/* Left arm raised */}
              <path
                d="M15 62 Q0 42 8 32"
                fill="none"
                stroke="#c4841a"
                strokeWidth="8"
                strokeLinecap="round"
              />
              {/* Right arm raised */}
              <path
                d="M105 62 Q120 42 112 32"
                fill="none"
                stroke="#c4841a"
                strokeWidth="8"
                strokeLinecap="round"
              />
            </>
          )}

          {expression === 'thumbsup' && (
            <>
              {/* Left arm resting */}
              <path
                d="M15 62 Q2 57 5 47"
                fill="none"
                stroke="#c4841a"
                strokeWidth="8"
                strokeLinecap="round"
              />
              {/* Right arm — thumbs up */}
              <path
                d="M105 62 Q118 52 115 39"
                fill="none"
                stroke="#c4841a"
                strokeWidth="8"
                strokeLinecap="round"
              />
              {/* Thumb */}
              <path
                d="M115 39 L112 31"
                fill="none"
                stroke="#c4841a"
                strokeWidth="6"
                strokeLinecap="round"
              />
              {/* Fist */}
              <circle cx="115" cy="39" r="5" fill="#c4841a" />
            </>
          )}

          {expression === 'happy' && (
            <>
              {/* Left arm */}
              <path
                d="M15 62 Q2 57 5 47"
                fill="none"
                stroke="#c4841a"
                strokeWidth="8"
                strokeLinecap="round"
              />
              {/* Right arm */}
              <path
                d="M105 62 Q118 57 115 47"
                fill="none"
                stroke="#c4841a"
                strokeWidth="8"
                strokeLinecap="round"
              />
            </>
          )}
        </>
      )}
    </svg>
  )
}
