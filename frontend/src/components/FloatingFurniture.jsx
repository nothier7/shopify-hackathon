import { motion, useScroll, useTransform, useSpring } from 'framer-motion';

const LOUNGE_CHAIR = 'https://media.base44.com/images/public/6a80912c91c49631c09bf1e5/e8e8e9150_generated_image.png';
const ARC_LAMP = 'https://media.base44.com/images/public/6a80912c91c49631c09bf1e5/86a2c57a2_generated_image.png';
const SOFA = 'https://media.base44.com/images/public/6a80912c91c49631c09bf1e5/9dabcc5ef_generated_image.png';
const VASE = 'https://media.base44.com/images/public/6a80912c91c49631c09bf1e5/ec3a012ec_generated_image.png';
const COFFEE_TABLE = 'https://media.base44.com/images/public/6a80912c91c49631c09bf1e5/2a5941820_generated_image.png';
const BOOKSHELF = 'https://media.base44.com/images/public/6a80912c91c49631c09bf1e5/18b58c8bd_generated_image.png';
const PENDANT = 'https://media.base44.com/images/public/6a80912c91c49631c09bf1e5/e35e83c69_generated_image.png';
const SIDE_TABLE = 'https://media.base44.com/images/public/6a80912c91c49631c09bf1e5/5b0cbf0c9_generated_image.png';

const BOUNCE_EASE = [0.34, 1.56, 0.64, 1];

const ELEMENTS = [
  { src: SOFA,         top: '-6%',    left: '-4%',   size: 480, delay: 0,   duration: 7,   opacity: 0.85, yMove: -24, xMove: 14,  baseRotate: 5,   rotateMove: 7,  parallax: 0.18 },
  { src: PENDANT,      top: '5%',     left: '40%',   size: 180, delay: 1,   duration: 6,   opacity: 0.75, yMove: -18, xMove: 10,  baseRotate: -8,  rotateMove: 12, parallax: -0.12 },
  { src: VASE,         top: '12%',    right: '6%',   size: 160, delay: 2,   duration: 5.5, opacity: 0.80, yMove: -16, xMove: -8,  baseRotate: 10,  rotateMove: 9,  parallax: 0.28 },
  { src: LOUNGE_CHAIR, top: '38%',    left: '-7%',   size: 380, delay: 0.5, duration: 7.5, opacity: 0.85, yMove: -22, xMove: 12,  baseRotate: -7,  rotateMove: -9, parallax: 0.22 },
  { src: BOOKSHELF,    top: '35%',    right: '-4%',  size: 360, delay: 0.8, duration: 7,   opacity: 0.80, yMove: -20, xMove: -12, baseRotate: 8,   rotateMove: -7, parallax: 0.20 },
  { src: ARC_LAMP,     bottom: '12%', left: '22%',   size: 280, delay: 2.5, duration: 6.8, opacity: 0.80, yMove: -18, xMove: 10,  baseRotate: -5,  rotateMove: 7,  parallax: 0.32 },
  { src: COFFEE_TABLE, bottom: '-6%', right: '15%',  size: 260, delay: 1.2, duration: 7,   opacity: 0.80, yMove: -20, xMove: 12,  baseRotate: 6,   rotateMove: 8,  parallax: 0.14 },
];

function FloatingFurnitureItem({ el, scrollY }) {
  const rawY = useTransform(scrollY, [0, 3000], [0, 3000 * el.parallax]);
  const y = useSpring(rawY, { stiffness: 40, damping: 18, mass: 0.6 });

  return (
    <motion.div
      style={{
        position: 'absolute',
        top: el.top,
        left: el.left,
        right: el.right,
        bottom: el.bottom,
        width: el.size,
        height: el.size,
        y,
      }}
    >
      <motion.img
        src={el.src}
        alt=""
        className="w-full h-full"
        style={{
          opacity: el.opacity,
          objectFit: 'contain',
          mixBlendMode: 'darken',
        }}
        animate={{
          y: [0, el.yMove, 0],
          x: [0, el.xMove, 0],
          rotate: [el.baseRotate, el.baseRotate + el.rotateMove, el.baseRotate],
          scale: [1, 1.03, 1],
        }}
        transition={{
          duration: el.duration,
          delay: el.delay,
          repeat: Infinity,
          ease: BOUNCE_EASE,
        }}
      />
    </motion.div>
  );
}

export default function FloatingFurniture({ subtle = false }) {
  const { scrollY } = useScroll();

  const elements = subtle
    ? ELEMENTS.map(e => ({ ...e, opacity: e.opacity * 0.5, size: Math.round(e.size * 0.65) }))
    : ELEMENTS;

  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none z-0" style={{ mixBlendMode: 'darken' }}>
      {elements.map((el, i) => (
        <FloatingFurnitureItem key={i} el={el} scrollY={scrollY} />
      ))}
    </div>
  );
}