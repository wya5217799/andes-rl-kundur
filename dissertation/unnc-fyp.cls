
\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{unnc-fyp}[2025/10/29 UNNC FYP Dissertation Class]

\DeclareOption*{\PassOptionsToClass{\CurrentOption}{report}}
\ProcessOptions\relax

\LoadClass[12pt,a4paper,oneside]{report}

\RequirePackage[margin=2.5cm]{geometry}
\RequirePackage{setspace}
\RequirePackage{titlesec}
\RequirePackage{tocloft}
\renewcommand{\cftchapfont}{\bfseries}
\renewcommand{\cftsecfont}{\normalfont}
\setlength{\cftbeforechapskip}{6pt}
\RequirePackage{newtxtext}
\RequirePackage{newtxmath}
\RequirePackage{graphicx}
\RequirePackage{caption}
\RequirePackage{booktabs}
\RequirePackage{array}
\RequirePackage{csquotes}
\RequirePackage[hidelinks]{hyperref}
\RequirePackage{enumitem}
\RequirePackage{amsmath}
\RequirePackage[utf8]{inputenc}

\setlength{\parindent}{1.27cm}
\setlength{\parskip}{12pt}
\onehalfspacing

\titleformat{\chapter}
  {\normalfont\bfseries\centering\fontsize{18pt}{22pt}\selectfont}
  {Chapter \thechapter}{1em}{}
\titlespacing*{\chapter}{0pt}{0pt}{24pt}

\titleformat{\section}
  {\normalfont\bfseries\fontsize{12pt}{14pt}\selectfont}{\thesection}{1em}{}
\titlespacing*{\section}{0pt}{0pt}{24pt}

\titleformat{\subsection}
  {\normalfont\fontsize{12pt}{14pt}\selectfont}{\thesubsection}{1em}{}
\titlespacing*{\subsection}{0pt}{0pt}{24pt}

\captionsetup{font=small,labelfont=normalfont,textfont=normalfont,justification=centering}

\numberwithin{figure}{chapter}
\numberwithin{table}{chapter}

\newcommand{\UNNCtitle}{}
\newcommand{\UNNCname}{}
\newcommand{\UNNCid}{}
\newcommand{\UNNCsupervisor}{}
\newcommand{\UNNCmoderator}{}
\newcommand{\UNNCdate}{}

\newcommand{\UNNCmaketitle}{
  \begin{titlepage}
    \centering
    \vspace*{1cm}
    {\Large \textbf{EEEE3056 \\ Third Year Project Dissertation}\par}
    \vspace{1.5cm}
    {\LARGE \textbf{\UNNCtitle}\par}
    \vspace{2cm}
    {\large \textbf{DEPARTMENT OF ELECTRICAL AND ELECTRONIC ENGINEERING}\\
    \textbf{UNIVERSITY OF NOTTINGHAM NINGBO CHINA}\par}
    \vspace{2cm}
    \begin{tabular}{@{}ll@{}}
      \textbf{Name:} & \UNNCname \\
      \textbf{Student ID:} & \UNNCid \\
      \textbf{Supervisor:} & \UNNCsupervisor \\
      \textbf{Moderator:} & \UNNCmoderator \\
      \textbf{Date:} & \UNNCdate \\
    \end{tabular}
    \vfill
    {\small Third Year Project Dissertation is submitted in part fulfillment of the requirements of the Degree of Bachelor of Engineering.\par}
  \end{titlepage}
}

\newenvironment{declaration}{
  \chapter*{Declaration}
}{}

\endinput
