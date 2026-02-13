export function Partners() {
  const partners = [
    {
      name: "Veterans Service Organization",
      logo: "https://placehold.co/200x100/e2e8f0/0a2463?text=Veterans+Service+Org",
      alt: "Veterans Service Organization"
    },
    {
      name: "Veterans Alliance",
      logo: "https://placehold.co/200x100/e2e8f0/0a2463?text=Veterans+Alliance",
      alt: "Veterans Alliance"
    },
    {
      name: "Military Foundation",
      logo: "https://placehold.co/200x100/e2e8f0/0a2463?text=Military+Foundation",
      alt: "Military Foundation"
    },
    {
      name: "Veterans Support Network",
      logo: "https://placehold.co/200x100/e2e8f0/0a2463?text=Veterans+Support+Network",
      alt: "Veterans Support Network"
    }
  ];

  return (
    <section className="py-16 bg-neutral-100">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-12">
          <h2 className="text-3xl font-bold text-navy mb-4">Our Partners</h2>
          <p className="text-lg text-muted-foreground max-w-3xl mx-auto">
            Valor Assist collaborates with trusted organizations to better serve veterans across the country.
          </p>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-8 items-center">
          {partners.map((partner, index) => (
            <div key={index} className="flex justify-center">
              <img
                src={partner.logo}
                alt={partner.alt}
                className="max-h-16 grayscale opacity-70 hover:grayscale-0 hover:opacity-100 transition-all duration-300"
              />
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}