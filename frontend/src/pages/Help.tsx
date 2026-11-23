import { Link } from 'react-router-dom'
import { Activity, ArrowRight, ClipboardList, Cog, HeartPulse, LayoutDashboard, UserRound } from 'lucide-react'

const pages = [
  {
    id: 'dashboard', title: 'Dashboard', path: '/', action: 'Open dashboard', icon: LayoutDashboard,
    description: 'Start a new analysis, see recent submissions, and open your account from the workspace overview.',
    steps: ['Recent analyses link to their result details.', 'The account panel shows whether you are signed in.'],
  },
  {
    id: 'outcome', title: 'Procedure outcome prediction', path: '/analyses/new', action: 'Start an analysis', icon: Activity,
    description: 'Open New Ablation Analysis and choose Outcome prediction. Upload a procedure file, choose an available model, review the inputs, and run the analysis.',
    steps: ['Accepts CSV, JSON, or XLSX files up to 10 MB.', 'For a multirow CSV, select the row to analyze in the preview.'],
  },
  {
    id: 'clustering', title: 'Ablation-site clustering', path: '/analyses/new', action: 'Open analysis options', icon: Activity,
    description: 'Choose the Ablation-site clustering tab on New Ablation Analysis. Upload one patient’s site records and review the cluster and PCA charts.',
    steps: ['Requires a whitespace-delimited TXT file with a header row, up to 10 MB.', 'The cluster describes site patterns; it is not an outcome prediction.'],
  },
  {
    id: 'heart', title: 'Heart disease detection', path: '/heart-disease', action: 'Open heart disease detection', icon: HeartPulse,
    description: 'Enter the fields supplied by the heart disease model and run a separate prediction.',
    steps: ['Shows the predicted class and probability of the model’s positive class.', 'The form appears only when the live model service is available.'],
  },
  {
    id: 'models', title: 'New Model', path: '/models/new', action: 'Open model training', icon: Cog,
    description: 'Upload a labeled dataset, enter its target column, and review the result of XGBoost training.',
    steps: ['Accepts CSV, JSON, or XLSX files up to 10 MB.', 'Training requires a signed-in account and the live API. The result shows validation metrics.'],
  },
  {
    id: 'history', title: 'Analyses', path: '/analyses', action: 'View analyses', icon: ClipboardList,
    description: 'Search and filter completed procedure outcome analyses, then open a record for its prediction and model details.',
    steps: ['Signed-in live analyses are saved to your account.', 'Signed-out analyses are available only during the current visit; demo records are examples.'],
  },
  {
    id: 'account', title: 'Account', path: '/account/create', action: 'Open account setup', icon: UserRound,
    description: 'Create an account or sign in to keep your analysis history and access model training.',
    steps: ['In live mode, you can change your password from My Account.', 'If you forget it, request a reset link from the sign-in page.'],
  },
]

export default function Help() {
  return <>
    <div className="page-heading"><div className="eyebrow"><span className="eyebrow-line"/> WORKSPACE GUIDE</div><h1>Help &amp; workflow</h1><p>Choose a task below to see what each page does and how to get started.</p></div>
    <div className="help-page-grid">
      {pages.map(page => <section className="work-card card-body help-page-card" aria-labelledby={`help-${page.id}`} key={page.id}>
        <div className="section-title"><span className="icon-box"><page.icon size={20}/></span><div><h2 id={`help-${page.id}`}>{page.title}</h2><p>{page.description}</p></div></div>
        <ul>{page.steps.map(step => <li key={step}>{step}</li>)}</ul>
        <Link className="text-button" to={page.path}>{page.action} <ArrowRight size={15}/></Link>
      </section>)}
    </div>
    <section className="work-card card-body help-faq" aria-labelledby="help-faq-title">
      <h2 id="help-faq-title">Common questions</h2>
      <details><summary>Can I use manual entry for an outcome prediction?</summary><p>Manual catheter entry is available for the demo. In live mode, the trained outcome models need recorded-data columns from a procedure file, so upload a file instead.</p></details>
      <details><summary>How do procedure file previews work?</summary><p>A multirow CSV lets you choose one row for prediction. JSON and XLSX uploads must each contain a single procedure. The preview groups V-numbered columns with the closest named column on their left; the original file is sent for analysis.</p></details>
      <details><summary>Which results appear under Analyses?</summary><p>Analyses lists completed procedure outcome predictions. Heart disease predictions and ablation-site clustering results appear on their own pages.</p></details>
      <details><summary>What do model performance metrics mean?</summary><p>They summarize evaluation across held-out rows from training. They do not measure certainty about one patient’s prediction. A dash means that metric was not supplied for the selected model.</p></details>
      <details><summary>Why is a model or page unavailable?</summary><p>A live model may be temporarily unavailable. Check the message on the page, or choose another available model where offered.</p></details>
      <details><summary>Why did my submission fail?</summary><p>Read the displayed error and check the file format, required fields, selected row, and model choice. Correct the inputs and try again.</p></details>
    </section>
  </>
}
