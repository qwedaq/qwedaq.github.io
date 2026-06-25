export const researchPillars = [
  {
    id: 'understand',
    index: '01',
    title: 'Understand',
    topics: ['Mechanistic Interpretability'],
    description:
      'Studying the internal representations, components, and computational mechanisms that contribute to model behaviour.'
  },
  {
    id: 'generalize',
    index: '02',
    title: 'Adapt & Generalize',
    topics: ['Domain Adaptation', 'Domain Generalization'],
    description:
      'Adapting models to changed target distributions and developing systems that remain effective on previously unseen domains.'
  },
  {
    id: 'evaluate',
    index: '03',
    title: 'Evaluate',
    topics: ['Robust Evaluation Frameworks'],
    description:
      'Designing evaluation systems that reveal capabilities and failures across modalities, tasks, and distribution shifts while producing grounded, interpretable evidence.'
  },
  {
    id: 'protect',
    index: '04',
    title: 'Trace & Protect',
    topics: ['Content Attribution', 'Content Protection'],
    description:
      'Studying how outputs relate to influential data or representations, and developing mechanisms for provenance, ownership verification, watermarking, and misuse deterrence.'
  },
  {
    id: 'optimize',
    index: '05',
    title: 'Optimize',
    topics: ['Inference Optimization'],
    description:
      'Reducing latency, memory, and computational cost while preserving model capability, output quality, and practical usability.'
  }
] as const;
