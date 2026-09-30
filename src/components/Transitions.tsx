import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';
import {Son} from './Son';

/** Flash d'appareil photo (changement de lieu). À poser à cheval sur une coupe. */
export const Flash: React.FC = () => {
  const frame = useCurrentFrame();
  const opacite = interpolate(frame, [0, 2, 9], [0, 1, 0], {extrapolateRight: 'clamp'});
  return (
    <AbsoluteFill style={{background: '#fffdf6', opacity: opacite, pointerEvents: 'none'}}>
      <Son nom="flash" volume={0.7} />
    </AbsoluteFill>
  );
};
