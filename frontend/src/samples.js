/**
 * Pre-configured realistic writing samples for testing and evaluation.
 */

export const SAMPLES = [
  {
    id: 'repetitive_transitions',
    label: 'Repetitive & Monotonous Sample',
    description: 'Contains repetitive sentence-initial transitions, repeated multiword phrases, and uniform sentence cadence.',
    text: `Furthermore, in the rapid development we observe steady results across each cluster. Furthermore, in the rapid development we notice consistent data from every ingestion node. Furthermore, in the rapid development we achieve similar outcomes throughout the entire pipeline. Additionally, the secondary processing engine aggregates quarterly telemetry records. Additionally, the reporting generator compiles monthly compliance digests. Additionally, the historical archiver compresses annual database snapshots.`
  },
  {
    id: 'wordy_technical',
    label: 'Wordy Technical Sample',
    description: 'Technical passage with bureaucratic padding, numbers, and citations to test preservation.',
    text: `In order to optimize pipeline throughput, the engineers must make a decision at this point in time. The deployment was executed for the purpose of benchmarking 10,000 transactions per second on AWS in London [1]. Due to the fact that memory consumption remained under 45%, the service is able to process incoming streams without difficulty. It is important to note that the primary database is not able to accept unauthenticated telemetry.`
  },
  {
    id: 'clean_academic',
    label: 'Clean Academic Sample',
    description: 'Realistic academic prose with natural variance and varied sentence structures.',
    text: `Neural language models generate remarkably fluent text, but their underlying architectures often favor high-probability tokens that produce predictable sentence lengths. While early statistical detectors relied on vocabulary perplexity (Vaswani et al., 2017), modern analysis emphasizes explainable stylistic observations. Researchers must evaluate whether observed cadences reflect human stylistic choice or artificial generation artifacts.`
  }
];
