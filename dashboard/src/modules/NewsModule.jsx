export function NewsModule({ news }) {
  const headlines = Array.isArray(news?.headlines) ? news.headlines : []

  return (
    <article className="module">
      <p className="module__label">05 · News</p>
      <h2 className="module__title">Headlines</h2>
      {headlines.length ? (
        <ul style={{ paddingLeft: '1.1rem', margin: 0 }}>
          {headlines.map((h, i) => (
            <li key={i} style={{ marginBottom: '0.4rem' }}>
              {h}
            </li>
          ))}
        </ul>
      ) : (
        <p style={{ margin: 0, opacity: 0.75 }}>No headlines returned.</p>
      )}
    </article>
  )
}
